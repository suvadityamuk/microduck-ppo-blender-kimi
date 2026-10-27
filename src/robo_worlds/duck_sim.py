"""CPU simulation of the Microduck in a generated world, the way it will run on the real robot.

* Physics: MuJoCo at 200 Hz with Pollen's BAM model of the XL330 servos (voltage-controlled DC motor + load-
  dependent friction), exactly as the policies are trained in mjlab.
* Low level: an ONNX walking policy (Pollen's stock walk or a world-specialised PPO policy) at 50 Hz on the
  61-D observation contract: ang vel, projected gravity, joint pos/vel, last action, 13-D command.
* High level: whoever calls `step(cmd13)` at 10 Hz (here, the planner expert) sets the command.
* World logic: pressure plates open their gates, hazards and falls end an episode, task progress is tracked.
* Domain randomisation for sim2real: servo voltage / sag, surface friction, light, materials, camera FOV/pose.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path

import mujoco
import numpy as np

from . import duck_scene as ds

DEFAULT_POSE = np.array([0.0, -0.0873, -0.4579, -0.0049, 0.4530, 0.3491, 0.3491, 0.0, 0.0,
                         0.0, 0.0873, 0.4579, 0.0049, -0.4530], np.float32)
CONTROL_HZ, HIGH_HZ = 50, 10
DECIMATION = 4          # physics steps per control step (dt 0.005)
FALL_TILT = math.radians(55)
GATE_SPEED = 0.35       # m/s the portcullis rises
BAM_KP_FW, BAM_VIN_RANGE, BAM_DROP_RANGE, BAM_VIN_MIN = 200.0, (6.5, 8.2), (0.0, 0.2), 6.0
BAM_STIFF_SOLREF_FRICTION = (-5.0e4, -2.0e2)
BAM_STIFF_SOLIMP_FRICTION = (0.99, 0.9999, 0.001, 0.5, 2.0)


@dataclass
class TaskState:
    task: dict
    phase: int = 0                  # index into the task's sub-goals
    plate_pressed: bool = False
    done: bool = False
    success: bool = False
    failure: str | None = None
    t: float = 0.0
    log: list = field(default_factory=list)


def _quat_rotate_inv(q, v):
    w, xyz = q[0], q[1:4]
    t = np.cross(xyz, v) * 2
    return v - w * t + np.cross(xyz, t)


class DuckSim:
    def __init__(self, world_dir, policy_onnx, seed=0, dr=True, render_size=(224, 224), head_fovy=70.0,
                 time_limit=None):
        import onnxruntime as ort

        self.scene = ds.load_scene(world_dir)
        self.world_dir = Path(world_dir)
        self.rng = np.random.default_rng(seed)
        self.dr = dr
        self.render_size = render_size
        self.head_fovy = head_fovy
        so = ort.SessionOptions()
        if os.environ.get("ORT_THREADS"):  # set to 1 when running many evals in parallel (else threads oversubscribe)
            so.intra_op_num_threads = so.inter_op_num_threads = int(os.environ["ORT_THREADS"])
        self.sess = ort.InferenceSession(str(policy_onnx), so)
        self.in_name = self.sess.get_inputs()[0].name
        self.zones = {z["name"]: z for z in self.scene["zones"]}
        self.plates = {p["name"]: p for p in self.scene.get("plates", [])}
        self.gates = self.scene.get("gates", {})
        self.tasks = {t["name"]: t for t in self.scene["tasks"]}
        self.time_limit = time_limit
        self._build()

    # ------------------------------------------------------------------ model
    def _build(self, light_scale=1.0, light_dir_jitter=(0.0, 0.0)):
        from bam.model import load_model
        from bam.mujoco import MujocoController

        spec = ds.world_spec(self.scene, light_scale=light_scale, light_dir_jitter=light_dir_jitter)
        robot = mujoco.MjSpec.from_file(str(ds.ROBOT_XML))
        for cam in robot.cameras:
            if cam.name == "head_camera":
                cam.fovy = self.head_fovy
        spec.attach(robot, frame=spec.worldbody.add_frame(pos=[0, 0, 0]), prefix="")
        sx, sy = self.scene["room"]["size"]
        spec.worldbody.add_camera(name="chase", pos=[-sx * 0.45, -sy * 0.45, 1.0], mode=mujoco.mjtCamLight.mjCAMLIGHT_TARGETBODY,
                                  targetbody="trunk_base", fovy=50)
        self.bam = load_model(motor_name="xl330", model="m6")
        self.bam.actuator.kp = BAM_KP_FW
        self.bam.actuator.vin = float(self.rng.uniform(*BAM_VIN_RANGE)) if self.dr else 7.4
        self.bam.actuator.max_current = None
        flim = self.bam.actuator.vin * self.bam.kt.value / self.bam.R.value
        names = []
        joints = {j.name: j for j in spec.joints}
        for act in spec.actuators:
            act.set_to_motor()
            act.forcelimited = True
            act.forcerange = (-flim, flim)
            act.ctrllimited = False
            act.gear = [1.0, 0, 0, 0, 0, 0]
            names.append(act.name)
            j = joints[act.target]
            j.damping = np.zeros((3, 1))
            j.frictionloss = 0.0
            j.solref_friction = BAM_STIFF_SOLREF_FRICTION
            j.solimp_friction = BAM_STIFF_SOLIMP_FRICTION
        self.m = spec.compile()
        self.m.opt.timestep = 0.005
        self.d = mujoco.MjData(self.m)
        drop = float(self.rng.uniform(*BAM_DROP_RANGE)) if self.dr else 0.1
        self.bam_ctrl = MujocoController(self.bam, names, self.m, self.d, vin_drop_gain=drop, vin_min=BAM_VIN_MIN)
        m = self.m
        self.qadr = [int(m.jnt_qposadr[m.actuator_trnid[i, 0]]) for i in range(m.nu)]
        self.vadr = [int(m.jnt_dofadr[m.actuator_trnid[i, 0]]) for i in range(m.nu)]
        fj = m.joint("trunk_base_freejoint")
        self.fq, self.fv = int(m.jnt_qposadr[fj.id]), int(m.jnt_dofadr[fj.id])
        self.trunk = m.body("trunk_base").id
        self.gyro = m.sensor_adr[m.sensor("imu_ang_vel").id]
        self.feet = [m.site("left_foot").id, m.site("right_foot").id]
        self.gate_q = {g: int(m.jnt_qposadr[m.joint(g + "_joint").id]) for g in self.gates}
        self.gate_v = {g: int(m.jnt_dofadr[m.joint(g + "_joint").id]) for g in self.gates}
        self.objects = [b for b in self.scene["bodies"] if b["kind"] == "object"]
        self.obj_q = {b["name"]: int(m.jnt_qposadr[m.joint(b["name"] + "_free").id]) for b in self.objects}
        self.obj_v = {b["name"]: int(m.jnt_dofadr[m.joint(b["name"] + "_free").id]) for b in self.objects}
        self.mat_rgba0 = m.mat_rgba.copy()
        self.geom_friction0 = m.geom_friction.copy()
        self.cam_pos0 = m.cam_pos.copy()
        self.light_diffuse0 = m.light_diffuse.copy()
        self.light_dir0 = m.light_dir.copy()
        self.renderers = {}
        self.hm = ds.height_map(self.scene)
        self.head_opt = mujoco.MjvOption()
        self.head_opt.geomgroup[:] = [1, 1, 0, 0, 1, 0]  # hide the robot's own shell (group 2) from its eye

    # ------------------------------------------------------------------ episode
    def reset(self, task_name, seed=None, start=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        m, d = self.m, self.d
        mujoco.mj_resetData(m, d)
        t = self.tasks[task_name]
        self.state = TaskState(task=t)
        if self.dr:
            self._randomize()
        x, y, yaw = start if start is not None else t["start"]
        if start is None:
            jx, jy, jyaw = t.get("start_jitter", (0.08, 0.08, 0.4))
            x, y, yaw = x + self.rng.uniform(-jx, jx), y + self.rng.uniform(-jy, jy), yaw + self.rng.uniform(-jyaw, jyaw)
        z0 = ds.STAND_Z + self._floor_h(x, y)
        d.qpos[self.fq:self.fq + 3] = [x, y, z0]
        d.qpos[self.fq + 3:self.fq + 7] = [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
        d.qpos[self.qadr] = DEFAULT_POSE
        for b in self.objects:
            a = self.obj_q[b["name"]]
            j = b["spawn"]["jitter"] if (self.dr and b.get("spawn")) else [0.0, 0.0]
            yawo = b["yaw"] + (self.rng.uniform(-1, 1) * b["spawn"]["yaw_jitter"] if self.dr and b.get("spawn") else 0.0)
            d.qpos[a:a + 3] = [b["pos"][0] + self.rng.uniform(-j[0], j[0]), b["pos"][1] + self.rng.uniform(-j[1], j[1]), b["pos"][2] + 0.002]
            d.qpos[a + 3:a + 7] = [math.cos(yawo / 2), 0, 0, math.sin(yawo / 2)]
        for g in self.gates:
            d.qpos[self.gate_q[g]] = 0.0
        self.gate_open = {g: False for g in self.gates}
        self.last_action = np.zeros(14, np.float32)
        self.cmd = np.zeros(13, np.float32)
        mujoco.mj_forward(m, d)
        self.bam_ctrl.reset(d.qpos)
        self.bam_ctrl.q_target[:] = DEFAULT_POSE
        self.time = 0.0
        for _ in range(int(0.4 * CONTROL_HZ)):  # settle on the spot with a zero command
            self._control_step()
        self.time = 0.0
        self.state.t = 0.0
        return self.observe()

    def _floor_h(self, x, y):
        m, d = self.m, self.d
        mujoco.mj_forward(m, d)
        gid = np.zeros(1, np.int32)
        dist = mujoco.mj_ray(m, d, np.array([x, y, 0.4]), np.array([0, 0, -1.0]), np.array([1, 0, 0, 0, 0, 0], np.uint8), 1, -1, gid)
        return 0.4 - dist if dist >= 0 else 0.0

    def _randomize(self):
        m = self.m
        r = self.rng
        # surfaces +-15 % friction, materials +-12 % colour, camera FOV and mount
        m.geom_friction[:, 0] = self.geom_friction0[:, 0] * r.uniform(0.85, 1.15, size=m.ngeom)
        m.mat_rgba[:, :3] = np.clip(self.mat_rgba0[:, :3] * r.uniform(0.88, 1.12, size=(m.nmat, 3)), 0, 1)
        cid = m.camera("head_camera").id
        m.cam_fovy[cid] = self.head_fovy + r.uniform(-6, 6)
        m.cam_pos[cid] = self.cam_pos0[cid] + r.uniform(-0.004, 0.004, 3)
        m.light_diffuse[:] = self.light_diffuse0 * r.uniform(0.6, 1.25)
        ld = self.light_dir0 + r.uniform(-0.25, 0.25, size=self.light_dir0.shape)
        m.light_dir[:] = ld / np.linalg.norm(ld, axis=1, keepdims=True)
        m.vis.headlight.ambient[:] = r.uniform(0.15, 0.45)
        self.bam.actuator.vin = float(r.uniform(*BAM_VIN_RANGE))

    # ------------------------------------------------------------------ control
    def _obs61(self):
        d = self.d
        q = d.xquat[self.trunk]
        grav = _quat_rotate_inv(q, np.array([0, 0, -1.0]))
        return np.concatenate([d.sensordata[self.gyro:self.gyro + 3], grav, d.qpos[self.qadr] - DEFAULT_POSE,
                               d.qvel[self.vadr], self.last_action, self.cmd]).astype(np.float32)

    def _control_step(self):
        a = self.sess.run(None, {self.in_name: self._obs61()[None]})[0][0].astype(np.float32)
        self.last_action = a
        self.bam_ctrl.q_target[:] = DEFAULT_POSE + a
        for _ in range(DECIMATION):
            self.bam_ctrl.update()
            mujoco.mj_step(self.m, self.d)
        self._world_logic(1.0 / CONTROL_HZ)
        self.time += 1.0 / CONTROL_HZ

    def _world_logic(self, dt):
        d = self.d
        feet = [d.site_xpos[f][:2] for f in self.feet]
        for p in self.plates.values():
            c, s, yaw = np.array(p["center"]), p["size"] / 2, p["yaw"]
            for f in feet:
                lx = (f - c) @ np.array([math.cos(yaw), math.sin(yaw)])
                ly = (f - c) @ np.array([-math.sin(yaw), math.cos(yaw)])
                if abs(lx) <= s and abs(ly) <= s:
                    if not self.gate_open.get(p["opens"], True):
                        self.gate_open[p["opens"]] = True
                    if self.state.task.get("plate") == p["name"]:
                        self.state.plate_pressed = True
        for g, info in self.gates.items():  # kinematic portcullis
            a = self.gate_q[g]
            target = info["travel"] if self.gate_open[g] else 0.0
            q = d.qpos[a]
            q = min(target, q + GATE_SPEED * dt) if target > q else max(target, q - GATE_SPEED * dt)
            d.qpos[a] = q
            d.qvel[self.gate_v[g]] = 0.0

    def step(self, cmd13):
        """Hold the 13-D command for one high-level tick (1/10 s). Returns (obs, done, info)."""
        self.cmd = np.asarray(cmd13, np.float32).copy()
        self.cmd[0] = np.clip(self.cmd[0], -0.4, 0.4)
        self.cmd[1] = np.clip(self.cmd[1], -0.2, 0.2)
        self.cmd[2] = np.clip(self.cmd[2], -1.5, 1.5)
        self.cmd[3:7] = np.clip(self.cmd[3:7], -1.0, 1.0)
        self.cmd[7:] = 0.0
        for _ in range(CONTROL_HZ // HIGH_HZ):
            self._control_step()
            self._monitor()
            if self.state.done:
                break
        return self.observe(), self.state.done, {"success": self.state.success, "failure": self.state.failure}

    # ------------------------------------------------------------------ task logic
    def pose(self):
        d = self.d
        p = d.qpos[self.fq:self.fq + 3].copy()
        q = d.qpos[self.fq + 3:self.fq + 7]
        yaw = math.atan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2))
        return p, yaw

    def object_pos(self, name):
        a = self.obj_q[name]
        return self.d.qpos[a:a + 3].copy()

    def tilt(self):
        q = self.d.xquat[self.trunk]
        g = _quat_rotate_inv(q, np.array([0, 0, -1.0]))
        return math.acos(float(np.clip(-g[2], -1, 1)))

    def subgoals(self, task=None):
        t = task or self.state.task
        if t["kind"] == "goto":
            return [("zone", t["goal"])]
        if t["kind"] == "gate":
            return [("plate", t["plate"]), ("zone", t["goal"])]
        if t["kind"] == "push":
            return [("object", t["object"], t["goal"])]
        return [("zone", g) for g in t["goals"]]

    def _in_zone(self, xy, zname, margin=0.0):
        z = self.zones[zname]
        return float(np.linalg.norm(xy - np.array(z["center"]))) <= z["radius"] - margin

    def _monitor(self):
        st = self.state
        st.t = self.time
        p, _ = self.pose()
        if self.tilt() > FALL_TILT or p[2] - self._floor_h_fast(p) < 0.07:
            st.done, st.failure = True, "fell"
            return
        for zn in st.task.get("avoid", []):
            if self._in_zone(p[:2], zn, margin=-0.02):
                st.done, st.failure = True, f"entered hazard {zn}"
                return
        goals = self.subgoals()
        if st.phase < len(goals):
            g = goals[st.phase]
            reached = False
            if g[0] == "zone":
                reached = self._in_zone(p[:2], g[1], margin=0.03)
            elif g[0] == "plate":
                reached = st.plate_pressed
            elif g[0] == "object":
                reached = self._in_zone(self.object_pos(g[1])[:2], g[2], margin=0.0)
            if reached:
                st.log.append((round(self.time, 2), g))
                st.phase += 1
        if st.phase >= len(goals):
            st.done, st.success = True, True
            return
        limit = self.time_limit or self.default_time_limit(st.task)
        if self.time >= limit:
            st.done, st.failure = True, "timeout"

    def _floor_h_fast(self, p):
        # local floor height under the trunk (cached height map when available)
        hm = getattr(self, "hm", None)
        if hm is None:
            return 0.0
        i = int(round((p[0] - hm["x0"]) / hm["res"]))
        j = int(round((p[1] - hm["y0"]) / hm["res"]))
        i, j = min(max(i, 0), hm["shape"][0] - 1), min(max(j, 0), hm["shape"][1] - 1)
        return float(min(hm["H"][i, j], 0.13))

    @staticmethod
    def default_time_limit(task):
        return {"goto": 60.0, "gate": 90.0, "push": 120.0, "visit": 100.0}[task["kind"]]

    # ------------------------------------------------------------------ rendering / observation
    def observe(self):
        p, yaw = self.pose()
        return {"pos": p, "yaw": yaw, "q": self.d.qpos[self.qadr].copy(), "dq": self.d.qvel[self.vadr].copy(),
                "cmd": self.cmd.copy(), "time": self.time}

    def render(self, camera="head_camera", size=None):
        h, w = size or self.render_size
        head = camera == "head_camera"
        # the head camera's image axes are a quarter turn off in the model: render transposed, rotate back
        key = (w, h) if head else (h, w)
        if key not in self.renderers:
            self.renderers[key] = mujoco.Renderer(self.m, *key)
        r = self.renderers[key]
        r.update_scene(self.d, camera=camera, scene_option=self.head_opt if head else None)
        img = r.render()
        return np.ascontiguousarray(np.rot90(img, k=-1)) if head else img

    def proprio(self):
        """The robot-side state given to the high-level policy: joint pos/vel, gravity, gyro, current command."""
        d = self.d
        grav = _quat_rotate_inv(d.xquat[self.trunk], np.array([0, 0, -1.0]))
        return np.concatenate([d.qpos[self.qadr], d.qvel[self.vadr] * 0.1, grav, d.sensordata[self.gyro:self.gyro + 3] * 0.2,
                               self.cmd[:7]]).astype(np.float32)
