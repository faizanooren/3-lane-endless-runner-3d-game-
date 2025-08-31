from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import time
import random

# perspective field-of-view
FOV_Y = 60                  
cam_pos = (0, -300, 200)

# Lanes, runner & movement
LANE_W = 100
LANE_X = [-LANE_W, 0, LANE_W]   # left/center/right X-positions

lane_idx = 1                     # start center lane
runner_forward = 0               # y-axis forward along track
runner_side = LANE_X[lane_idx]   # x-axis along lanes
runner_side_goal = runner_side   # smooth lane switching target

# Animation pacing
track_scroll = 0
base_speed = 0.7
game_speed = base_speed
max_speed = 4
lane_interp_speed = 5

# Runner animation (speeds up with distance)
anim_base = 0.02
anim_max = 0.05
anim_curr = anim_base


# Game state & score
is_running = True
score = 0
points = 0
meters = 0.0
t_start = None
t_pause_begin = None
is_fp = False    
lives = 5

# Arms swing tuning
ARM_SWING_MAX = 5
ARM_SWING_RATE = 0.02

# Day/Night
is_day = False
bg_rgb = [0.2, 0.3, 0.5]
is_transitioning = False
trans_dir = 0            # +1 night to day, -1 day to night
trans_step = 0.01

#coins
coins = []
coin_t = 0.0
coin_period = 2.0
coin_pick_radius = 15
coin_double_prob = 0.25

#obstacles
obstacles = []
ob_t = 0.0
ob_period = 3.5
hit_radius = 20
min_y_gap = 800

#magnet
magnets = []
mg_t = 0.0
mg_period = 25
mag_on = False
mag_time_left = 0.0
mag_seconds = 10
mag_radius = 500
mag_pick_radius = 15
mag_pull = 15.0

def reset_game():
    global lane_idx, runner_forward, runner_side, runner_side_goal
    global track_scroll, game_speed, is_running, score, points
    global meters, t_start, t_pause_begin, coins, coin_t
    global obstacles, ob_t, anim_curr, lives
    global magnets, mg_t, mag_on, mag_time_left

    # Reset player position to center lane
    lane_idx = 1
    runner_forward = 0
    runner_side = LANE_X[lane_idx]
    runner_side_goal = runner_side

    # Reset movement and animation
    track_scroll = 0
    game_speed = base_speed
    anim_curr = anim_base

    # Reset game state
    is_running = True
    score = 0
    points = 0
    meters = 0.0

    # Reset timing
    t_start = time.time()
    t_pause_begin = None

    # Clear all collectible items
    coins = []
    coin_t = 0.0

    obstacles = []
    ob_t = 0.0

    lives = 5

    # Reset power-ups
    magnets = []
    mg_t = 0.0
    mag_on = False
    mag_time_left = 0.0


def draw_bg(): #2D
    glDisable(GL_DEPTH_TEST)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(-1, 1, -1, 1)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glColor3f(bg_rgb[0], bg_rgb[1], bg_rgb[2])
    glBegin(GL_QUADS)
    glVertex2f(-1, -1)
    glVertex2f( 1, -1)
    glVertex2f( 1,  1)
    glVertex2f(-1,  1)
    glEnd()

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_DEPTH_TEST)


def draw_text(x, y, s, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1200, 0, 800)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glRasterPos2f(x, y)
    for ch in s:
        glutBitmapCharacter(font, ord(ch))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_ground():
    glColor3f(0.2, 0.8, 0.2)
    glBegin(GL_QUADS)
    g = 1000
    glVertex3f(-g, -g, -5)
    glVertex3f( g, -g, -5)
    glVertex3f( g,  g, -5)
    glVertex3f(-g,  g, -5)
    glEnd()

    glColor3f(0.6, 0.3, 0.1)
    h = 50
    road_w = LANE_W * 3

    # left barrier
    glBegin(GL_QUADS)
    glVertex3f(-road_w/2 - 20, -1000, 0)
    glVertex3f(-road_w/2 - 20,  1000, 0)
    glVertex3f(-road_w/2 - 20,  1000, h)
    glVertex3f(-road_w/2 - 20, -1000, h)
    glEnd()

    # right barrier
    glBegin(GL_QUADS)
    glVertex3f( road_w/2 + 20, -1000, 0)
    glVertex3f( road_w/2 + 20,  1000, 0)
    glVertex3f( road_w/2 + 20,  1000, h)
    glVertex3f( road_w/2 + 20, -1000, h)
    glEnd()


def draw_trees():
    day_k = 1.0 if is_day else 0.4
    road_w = LANE_W * 3
    tree_x = road_w/2 + 80
    step = 150

    for side in (-1, 1):
        x_pos = side * tree_x
        for i in range(-15, 25):
            z_pos = i * step - (track_scroll % step)
            random.seed(i + side * 100)
            s = random.uniform(0.8, 1.2)
            trunk_h = 25 * s
            crown = 15 * s

            glPushMatrix()
            glTranslatef(x_pos, z_pos, trunk_h/2)
            glColor3f(0.4 * day_k, 0.2 * day_k, 0.1 * day_k)
            glScalef(3, 3, trunk_h)
            glutSolidCube(1)
            glPopMatrix()

            glPushMatrix()
            glTranslatef(x_pos, z_pos, trunk_h + crown/2)
            glColor3f(0.1 * day_k, 0.6 * day_k, 0.1 * day_k)
            gluSphere(gluNewQuadric(), crown, 8, 8)
            glPopMatrix()


def draw_track():
    glColor3f(0.3, 0.3, 0.3)
    glBegin(GL_QUADS)

    t_len = 2000
    t_w = LANE_W * 3
    glVertex3f(-t_w/2, -t_len, 0)
    glVertex3f( t_w/2, -t_len, 0)
    glVertex3f( t_w/2,  t_len, 0)
    glVertex3f(-t_w/2,  t_len, 0)
    glEnd()

    glColor3f(1, 1, 0)
    gap = 100
    count = int(t_len * 2 / gap) + 5

    for i in range(count):
        y = (i * gap) - t_len - (track_scroll % gap)

        glBegin(GL_QUADS)
        glVertex3f(-LANE_W/2 - 2, y, 1)
        glVertex3f(-LANE_W/2 + 2, y, 1)
        glVertex3f(-LANE_W/2 + 2, y + gap/2, 1)
        glVertex3f(-LANE_W/2 - 2, y + gap/2, 1)
        glEnd()

        glBegin(GL_QUADS)
        glVertex3f( LANE_W/2 - 2, y, 1)
        glVertex3f( LANE_W/2 + 2, y, 1)
        glVertex3f( LANE_W/2 + 2, y + gap/2, 1)
        glVertex3f( LANE_W/2 - 2, y + gap/2, 1)
        glEnd()

def draw_coin(x, y, z, kind="normal"):
    glPushMatrix()
    glTranslatef(x, y, z)
    if kind == "double":
        glColor3f(1, 1, 0)
    else:
        glColor3f(0.9,0.9,0.9)
    gluSphere(gluNewQuadric(), 10, 10, 10)
    glPopMatrix()


def draw_magnet(x, y, z):
    glPushMatrix()
    glTranslatef(x, y, z)

    glColor3f(1, 0.4, 0.8)
    glPushMatrix()
    glRotatef(90, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 4, 4, 12, 8, 8)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0, -6, 0)
    glColor3f(1, 0, 0)
    gluCylinder(gluNewQuadric(), 4.5, 4.5, 2, 8, 8)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0, 6, 0)
    glColor3f(0, 0, 1)
    gluCylinder(gluNewQuadric(), 4.5, 4.5, 2, 8, 8)
    glPopMatrix()

    glColor3f(0.8, 0.8, 0.8)
    glBegin(GL_LINES)
    for i in range(8):
        ang = i * 45
        r = 15
        x1 = r * math.cos(math.radians(ang))
        z1 = r * math.sin(math.radians(ang))
        x2 = (r + 5) * math.cos(math.radians(ang))
        z2 = (r + 5) * math.sin(math.radians(ang))
        glVertex3f(x1, 0, z1)
        glVertex3f(x2, 0, z2)
    glEnd()

    glPopMatrix()


def draw_obstacle(x, y, z, kind="normal"):
    glPushMatrix()
    glTranslatef(x, y, z)
    if kind == "life":
        glColor3f(0, 0, 0)
    else:
        glColor3f(1, 0, 0)
    glutSolidCube(20)
    glPopMatrix()


def draw_runner():
    glPushMatrix()
    # Position character at current lane and forward position
    glTranslatef(runner_side, runner_forward, 20)

    # animation phase for running motion
    phase = (track_scroll * anim_curr) % (2 * math.pi)
    leg_stride = math.sin(phase) * 4          # Leg movement
    arm_swing = math.sin(phase + math.pi) * ARM_SWING_MAX  # Arms opposite to legs
    # character drawing
    glPushMatrix()
    if is_day:
        glColor3f(0, 0.5, 1)      # Blue shirt in daylight
    else:
        glColor3f(0.4, 0.4, 0.4)  # Gray shirt at night
    glScalef(1.2, 0.8, 1.8)       # Make rectangular torso
    glutSolidCube(15)
    glPopMatrix()

    
    glPushMatrix()
    glTranslatef(0, 0, 18)
    glColor3f(1, 0.8, 0.6)        # Skin color
    gluSphere(gluNewQuadric(), 8, 10, 10)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0, 0, 25)
    glColor3f(0.3, 0.2, 0.1)
    gluSphere(gluNewQuadric(), 8.5, 8, 8)
    glPopMatrix()

    base_bias = -5.0
    glPushMatrix()
    glTranslatef(-12, 0, 10)
    glRotatef(base_bias + arm_swing, 1, 0, 0)
    glRotatef(90, 1, 0, 0)
    glColor3f(1, 0.8, 0.6)
    gluCylinder(gluNewQuadric(), 2, 2, 12, 8, 8)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(12, 0, 10)
    glRotatef(base_bias - arm_swing, 1, 0, 0)
    glRotatef(90, 1, 0, 0)
    glColor3f(1, 0.8, 0.6)
    gluCylinder(gluNewQuadric(), 2, 2, 12, 8, 8)
    glPopMatrix()

    hip_z = -13.5
    leg_h = 14.0

    glPushMatrix()
    glTranslatef(-5, 0, hip_z)
    glRotatef(leg_stride, 1, 0, 0)
    glRotatef(180, 1, 0, 0)
    if is_day:
        glColor3f(0.2, 0.2, 0.8)
    else:
        glColor3f(0.1, 0.1, 0.1)
    gluCylinder(gluNewQuadric(), 3, 3, leg_h, 8, 8)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(5, 0, hip_z)
    glRotatef(-leg_stride, 1, 0, 0)
    glRotatef(180, 1, 0, 0)
    if is_day:
        glColor3f(0.2, 0.2, 0.8)
    else:
        glColor3f(0.1, 0.1, 0.1)
    gluCylinder(gluNewQuadric(), 3, 3, leg_h, 8, 8)
    glPopMatrix()

    foot_z = hip_z - leg_h - 1.0
    glPushMatrix()
    glTranslatef(-5, 2, foot_z)
    glColor3f(0.1, 0.1, 0.1)
    glScalef(0.8, 1.2, 0.4)
    glutSolidCube(6)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(5, 2, foot_z)
    glColor3f(0.1, 0.1, 0.1)
    glScalef(0.8, 1.2, 0.4)
    glutSolidCube(6)
    glPopMatrix()

    glPopMatrix()



def draw_all_coins():
    for c in coins:
        draw_coin(c['x'], c['y'], c['z'], c.get('type', 'normal'))


def draw_all_magnets():
    for m in magnets:
        draw_magnet(m['x'], m['y'], m['z'])


def draw_all_obstacles():
    for o in obstacles:
        draw_obstacle(o['x'], o['y'], o['z'], o.get('type', 'normal'))




#spawn
def spot_ok(nx, ny, is_ob=False, is_coin=False, is_mg=False):
    min_gap = 150
    coin_gap = 100

    for ob in obstacles:
        if abs(ob['y'] - ny) < min_y_gap and ob['x'] == nx:
            return False

    if is_coin or is_ob or is_mg:
        for c in coins:
            d = math.hypot(c['x'] - nx, c['y'] - ny)
            if d < coin_gap:
                return False

    if is_coin or is_ob or is_mg:
        for m in magnets:
            d = math.hypot(m['x'] - nx, m['y'] - ny)
            if d < min_gap:
                return False

    if is_ob:
        nearby = []
        for ob in obstacles:
            if abs(ob['y'] - ny) < min_gap:
                nearby.append(ob['x'])
        blocked = set(nearby + [nx])
        if len(blocked) >= 3:
            return False

    return True


def emit_coin():
    tries = 0
    while tries < 15:
        lane = random.randint(0, 2)                    # Pick random lane
        x = LANE_X[lane]
        y = runner_forward + 300 + random.randint(50, 250)  # Spawn ahead of player
        z = 20

        # coin type: normal (1 point) or double (2 points)
        kind = "double" if random.random() < coin_double_prob else "normal"

        # Check if position doesn't overlap with other objects
        if spot_ok(x, y, is_coin=True):
            coins.append({'x': x, 'y': y, 'z': z, 'type': kind})
            return
        tries += 1


def emit_obstacles():
    tries = 0
    while tries < 15:
        how_many = random.randint(1, 2)

        recent = [ob['x'] for ob in obstacles[-6:]]
        use = {
            LANE_X[0]: recent.count(LANE_X[0]),
            LANE_X[1]: recent.count(LANE_X[1]),
            LANE_X[2]: recent.count(LANE_X[2]),
        }
        lanes_sorted = sorted(use.keys(), key=lambda k: use[k])

        if how_many == 1:
            if random.random() < 0.6:
                chosen = [lanes_sorted[0]]
            else:
                chosen = [random.choice(LANE_X)]
        else:
            if random.random() < 0.7:
                chosen = lanes_sorted[:2]
            else:
                chosen = random.sample(LANE_X, 2)

        ok = True
        newlist = []
        base_y = runner_forward + 400 + random.randint(50, 150)
        for lane_x in chosen:
            x = lane_x
            y = base_y + random.randint(-20, 20)
            z = 10
            kind = "life" if random.random() < 0.25 else "normal"
            if not spot_ok(x, y, is_ob=True):
                ok = False
                break
            newlist.append({'x': x, 'y': y, 'z': z, 'type': kind})

        occ = [o['x'] for o in newlist]
        free = [p for p in LANE_X if p not in occ]

        if ok and newlist and len(free) > 0:
            obstacles.extend(newlist)
            return

        tries += 1


def emit_magnet():
    tries = 0
    while tries < 15:
        lane = random.randint(0, 2)
        x = LANE_X[lane]
        y = runner_forward + 350 + random.randint(50, 200)
        z = 25
        if spot_ok(x, y, is_mg=True):
            magnets.append({'x': x, 'y': y, 'z': z})
            return
        tries += 1


def update_daynight():
    global bg_rgb, is_day, is_transitioning, trans_dir
    if is_transitioning:
        if trans_dir == 1:
            bg_rgb[0] = min(0.5, bg_rgb[0] + trans_step)
            bg_rgb[1] = min(0.8, bg_rgb[1] + trans_step * 2)
            bg_rgb[2] = min(1.0, bg_rgb[2] + trans_step * 3)
            if bg_rgb[2] >= 1.0:
                is_day = True
                is_transitioning = False
        elif trans_dir == -1:
            bg_rgb[0] = max(0.05, bg_rgb[0] - trans_step)
            bg_rgb[1] = max(0.05, bg_rgb[1] - (trans_step * 2))
            bg_rgb[2] = max(0.08, bg_rgb[2] - (trans_step * 2))
            if bg_rgb[1] <= 0.05:
                is_day = False
                is_transitioning = False


def update_coins():
    global points, coins
    for c in coins[:]:
        # Move coins toward player
        c['y'] -= game_speed

        # Remove coins that are behind the player
        if c['y'] < runner_forward - 50:
            coins.remove(c)
            continue

        # Magnetic attraction when magnet power-up is active
        if mag_on:
            dx = runner_side - c['x']
            dy = runner_forward - c['y']
            dz = 20 - c['z']
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            if dist < mag_radius:        # Within magnetic field
                if dist > 0:
                    kx = dx / dist * mag_pull
                    ky = dy / dist * mag_pull
                    kz = dz / dist * mag_pull
                    c['x'] += kx
                    c['y'] += ky
                    c['z'] += kz
                if dist < coin_pick_radius:
                    if c.get('type', 'normal') == "double":
                        points += 2
                        print(f"Magnet collected double coin! +2 points. Total points: {points}")
                    else:
                        points += 1
                        print(f"Magnet collected coin! +1 point. Total points: {points}")
                    coins.remove(c)
                continue

        d = math.sqrt((c['x'] - runner_side)**2 + (c['y'] - runner_forward)**2 + (c['z'] - 20)**2)
        if d < coin_pick_radius:
            if c.get('type', 'normal') == "double":
                points += 2
                print(f"Double coin collected! +2 points. Total points: {points}")
            else:
                points += 1
                print(f"Coin collected! +1 point. Total points: {points}")
            coins.remove(c)


def update_obstacles():
    global is_running, obstacles, lives
    for o in obstacles[:]:
        # Move obstacles toward player
        o['y'] -= game_speed
        if o['y'] < runner_forward - 50:
            obstacles.remove(o)
            continue

        # Check collision with player
        d = math.sqrt((o['x'] - runner_side)**2 + (o['y'] - runner_forward)**2 + (o['z'] - 10)**2)
        if d < hit_radius:
            if o.get('type', 'normal') == "life":
                lives -= 1
                print(f"Black box hit! Life remaining: {lives}")
                obstacles.remove(o)
                if lives <= 0:
                    is_running = False
                    print(f"Game Over! Final points: {points}")
                    break
            else:
                is_running = False
                print(f"Game Over! Final points: {points}")
                break


def update_magnets():
    global magnets, mag_on, mag_time_left
    for m in magnets[:]:
        m['y'] -= game_speed
        if m['y'] < runner_forward - 50:
            magnets.remove(m)
            continue

        d = math.sqrt((m['x'] - runner_side)**2 + (m['y'] - runner_forward)**2 + (m['z'] - 20)**2)
        if d < mag_pick_radius:
            magnets.remove(m)
            mag_on = True
            mag_time_left += mag_seconds
            print(f"Magnet collected! Active for {mag_time_left:.1f} more seconds")


def update_game():
    global runner_side, runner_side_goal, track_scroll, score, meters, game_speed, t_start
    global coin_t, ob_t, mg_t, anim_curr, mag_on, mag_time_left

    if not is_running or t_start is None:
        return

    # distance traveled (time-based)
    now = time.time()
    meters = now - t_start

    # Smooth lane switching animation
    diff = runner_side_goal - runner_side
    if abs(diff) > 0.5:
        runner_side += diff * 0.15      # Interpolate to target position
    else:
        runner_side = runner_side_goal

    # track scrolling effect
    track_scroll += game_speed

    # Gradually increase game speed
    speed_gain = min(meters / 15.0, max_speed - base_speed)
    game_speed = base_speed + speed_gain * 0.7

    # Increase animation speed to match game speed
    anim_gain = min(meters / 15.0, anim_max - anim_base)
    anim_curr = anim_base + anim_gain * 0.7

    # Update magnet power-up timer
    if mag_on:
        mag_time_left -= 0.016
        if mag_time_left <= 0:
            mag_on = False
            mag_time_left = 0.0
            print("Magnet effect ended")

    score += 1

    update_coins()
    update_obstacles()
    update_magnets()
    update_daynight()

    coin_t += 0.016
    if coin_t >= coin_period:
        emit_coin()
        coin_t = 0.0

    ob_t += 0.016
    if ob_t >= ob_period:
        emit_obstacles()
        ob_t = 0.0

    mg_t += 0.016
    if mg_t >= mg_period:
        emit_magnet()
        mg_t = 0.0



# Input handlers
def keyboardListener(key, x, y):
    global is_running, lane_idx, runner_side_goal, t_start, t_pause_begin
    global is_transitioning, trans_dir, is_day

    # R key resets the game
    if key == b'r':
        reset_game()
        print("Game Reset!")
        return

    # Spacebar pauses/resumes the game
    if key == b' ':
        if is_running:
            is_running = False
            t_pause_begin = time.time()    # Track pause start time
            print("Paused")
        else:
            # Resume: adjust timer to exclude pause duration
            if t_pause_begin is not None and t_start is not None:
                paused = time.time() - t_pause_begin
                t_start += paused
            is_running = True
            t_pause_begin = None
            print("Resumed")

    if key == b'd':
        if not is_day and not is_transitioning:
            is_transitioning = True
            trans_dir = 1
            print("Transitioning to day...")
    elif key == b'a':
        if is_day and not is_transitioning:
            is_transitioning = True
            trans_dir = -1
            print("Transitioning to night...")


def specialKeyListener(key, x, y):
    global cam_pos, lane_idx, runner_side_goal, runner_side
    cx, cy, cz = cam_pos

    # Up/Down arrows adjust camera height
    if key == GLUT_KEY_UP:
        cz += 5                    # camera up
    if key == GLUT_KEY_DOWN:
        cz -= 5                    # camera down

    # Left/Right arrows switch lanes
    if key == GLUT_KEY_LEFT:
        if lane_idx > 0 and abs(runner_side - runner_side_goal) < 5:
            lane_idx -= 1
            runner_side_goal = LANE_X[lane_idx]
            print(f"Switching to lane {lane_idx}")

    if key == GLUT_KEY_RIGHT:
        if lane_idx < 2 and abs(runner_side - runner_side_goal) < 5:
            lane_idx += 1
            runner_side_goal = LANE_X[lane_idx]
            print(f"Switching to lane {lane_idx}")

    cam_pos = (cx, cy, cz)


def mouse(button, state, x, y):
    global is_fp
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        is_fp = not is_fp
        if is_fp:
            print("Switched to First-Person View")
        else:
            print("Switched to Third-Person View")



# Camera & render pipeline
def setup_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV_Y, 1.25, 0.1, 1500)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    cx, cy, cz = cam_pos

    if is_fp:
        cam_x = runner_side
        cam_y = runner_forward + 10
        cam_z = 10
    else:
        cam_x = runner_side * 0.3
        cam_y = runner_forward + cy
        cam_z = cz

    gluLookAt(cam_x, cam_y, cam_z,
              runner_side * 0.5, runner_forward + 100, 10,
              0, 0, 1)


def render_world():
    draw_ground()          
    draw_trees()           
    draw_track()           
    draw_runner()          
    draw_all_coins()        
    draw_all_magnets()      
    draw_all_obstacles()    


def idle():
    update_game()           
    glutPostRedisplay()     


def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    draw_bg()

    glEnable(GL_DEPTH_TEST)
    setup_camera()
    render_world()

    draw_text(10, 670, f"Distance Travelled: {meters:.1f}m")
    draw_text(10, 640, f"Points: {points}")
    draw_text(10, 610, f"Life: {lives}")

    if mag_on:
        draw_text(10, 580, f"Magnet: ACTIVE ({mag_time_left:.1f}s)")
    else:
        draw_text(10, 580, f"Magnet: INACTIVE")

    draw_text(10, 550, f"Press 'r' to restart")
    draw_text(10, 520, f"Gold coins = 2 points, Silver coins = 1 point")
    draw_text(10, 490, f"'d' = day, 'a' = night")
    draw_text(10, 460, f"Mode: {'DAY' if is_day else 'NIGHT'}")
    draw_text(10, 490, f"")

    if not is_running:
        glColor3f(1, 1, 1)
        draw_text(500, 400, "PAUSED")
        if t_pause_begin is None:
            draw_text(450, 350, "GAME OVER")
            draw_text(430, 300, f"Final Points: {points}")

    glutSwapBuffers()


def main():
    """Initialize OpenGL window and start the game"""
    global t_start
    # Initialize GLUT 
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)  
    glutInitWindowSize(1000, 800)                             
    glutInitWindowPosition(0, 0)                              
    glutCreateWindow(b"3D Runner Game")                        

    glutDisplayFunc(showScreen)     
    glutKeyboardFunc(keyboardListener)      
    glutSpecialFunc(specialKeyListener)   
    glutMouseFunc(mouse)       
    glutIdleFunc(idle)         


    t_start = time.time()
    glutMainLoop()


if __name__ == "__main__":
    main()
