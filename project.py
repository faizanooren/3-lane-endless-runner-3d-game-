from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import time
import random

# Camera-related variables
camera_pos = (0, -300, 200)  # Position camera behind and above the runner

fovY = 60  # Field of view
GRID_LENGTH = 600  # Length of grid lines
rand_var = 423

# Game variables
LANE_WIDTH = 100  # Width of each lane
LANE_POSITIONS = [-LANE_WIDTH, 0, LANE_WIDTH]  # Left, Center, Right lane positions
current_lane = 1  # Start in center lane (0=left, 1=center, 2=right)
runner_z_pos = 0  # Runner's forward position
runner_x_pos = LANE_POSITIONS[current_lane]  # Runner's side position
runner_target_x = runner_x_pos  # Target position for smooth lane switching

# Animation variables
track_offset = 0  # For moving track effect
game_speed = 0.5  # Starting game movement speed (much slower)
base_speed = 0.5  # Base speed (reduced)
max_speed = 3  # Maximum speed (reduced)
lane_transition_speed = 5  # Speed of lane switching animation

# Game state
game_running = True           # Also used as "not paused"
score = 0
points = 0                    # Points from collecting coins
distance_covered = 0.0        # Total distance traveled (float for precision)
start_time = None             # Track when game started (or last resumed)
pause_start = None            # Time when pause began
first_person_view = False  # False = third-person view, True = first-person view

# Arm swing tuning (bigger swing for running)
ARM_SWING_MAX_DEG = 5     # amplitude (degrees) – larger for a running feel
ARM_SWING_SPEED = 0.02        # swing speed multiplier

# Coin system
coins = []  # List to store active coins
coin_spawn_timer = 0  # Timer for coin spawning
coin_spawn_interval = 2.0  # Time between coin spawns (seconds)
coin_collection_distance = 15  # Distance at which coins are collected

# Obstacle system
obstacles = []  # List to store active obstacles
obstacle_spawn_timer = 0  # Timer for obstacle spawning
obstacle_spawn_interval = 3.0  # Time between obstacle spawns (seconds)
obstacle_collision_distance = 20  # Distance at which obstacles cause collision
min_vertical_gap = 500 # Minimum vertical gap between obstacles

def reset_game():
    """Reset all game variables to initial state"""
    global current_lane, runner_z_pos, runner_x_pos, runner_target_x
    global track_offset, game_speed, game_running, score, points
    global distance_covered, start_time, pause_start, coins, coin_spawn_timer
    global obstacles, obstacle_spawn_timer
    
    current_lane = 1
    runner_z_pos = 0
    runner_x_pos = LANE_POSITIONS[current_lane]
    runner_target_x = runner_x_pos
    track_offset = 0
    game_speed = base_speed  # Reset to base speed
    game_running = True
    score = 0
    points = 0
    distance_covered = 0.0
    start_time = time.time()  # Reset start time
    pause_start = None
    coins = []  # Clear all coins
    coin_spawn_timer = 0
    obstacles = []  # Clear all obstacles
    obstacle_spawn_timer = 0

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1200, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_track():
    """Draw the 3-lane track with lane markers"""
    # Draw main track surface
    glColor3f(0.3, 0.3, 0.3)  # Dark gray track
    glBegin(GL_QUADS)
    
    track_length = 2000
    track_width = LANE_WIDTH * 3
    
    # Main track surface
    glVertex3f(-track_width/2, -track_length, 0)
    glVertex3f(track_width/2, -track_length, 0)
    glVertex3f(track_width/2, track_length, 0)
    glVertex3f(-track_width/2, track_length, 0)
    
    glEnd()
    
    # Draw lane dividers
    glColor3f(1, 1, 0)  # Yellow lane markers
    glLineWidth(3)
    
    # Animate lane markers moving towards the runner
    marker_spacing = 100
    num_markers = int(track_length * 2 / marker_spacing) + 5
    
    for i in range(num_markers):
        y_pos = (i * marker_spacing) - track_length - (track_offset % marker_spacing)

        
        # Left lane divider
        glBegin(GL_LINES)
        glVertex3f(-LANE_WIDTH/2, y_pos, 1)
        glVertex3f(-LANE_WIDTH/2, y_pos + marker_spacing/2, 1)
        glEnd()
        
        # Right lane divider
        glBegin(GL_LINES)
        glVertex3f(LANE_WIDTH/2, y_pos, 1)
        glVertex3f(LANE_WIDTH/2, y_pos + marker_spacing/2, 1)
        glEnd()

def draw_runner():
    """Draw the runner character with detailed body parts"""
    glPushMatrix()
    
    # Position the runner
    glTranslatef(runner_x_pos, runner_z_pos, 20)  # Slightly above ground
    
    run_cycle_legs = (track_offset * 0.02) % (2 * math.pi)
    leg_stride = math.sin(run_cycle_legs) * 4

    # Arms opposite phase to legs
    arm_swing = math.sin(run_cycle_legs + math.pi) * ARM_SWING_MAX_DEG
    
    # Runner body (rectangular torso)
    glPushMatrix()
    glColor3f(0, 0.5, 1)  # Blue shirt
    glScalef(1.2, 0.8, 1.8)  # Make it more rectangular
    glutSolidCube(15)
    glPopMatrix()
    
    # Runner head (sphere)
    glPushMatrix()
    glTranslatef(0, 0, 18)
    glColor3f(1, 0.8, 0.6)  # Skin color
    glutSolidSphere(8, 10, 10)  # radius, slices, stacks
    glPopMatrix()
    
    # Hair (dark sphere on top of head)
    glPushMatrix()
    glTranslatef(0, 0, 25)
    glColor3f(0.3, 0.2, 0.1)  # Brown hair
    glutSolidSphere(8.5, 8, 8)  # Slightly larger than head
    glPopMatrix()
    
    # ---- ARMS: bigger back-and-forth swing ----
    # We rotate first to give a neutral "slight backward" pose, then add +/- swing.
    # Arm geometry points down after a 90° X-rotation.
    base_arm_bias = -5.0  # slight backwards bias looks more like running
    # Left Arm
    glPushMatrix()
    glTranslatef(-12, 0, 10)
    glRotatef(base_arm_bias + arm_swing, 1, 0, 0)  # larger swing
    glRotatef(90, 1, 0, 0)  # point cylinder down
    glColor3f(1, 0.8, 0.6)
    gluCylinder(gluNewQuadric(), 2, 2, 12, 8, 8)
    glPopMatrix()
    
    # Right Arm (opposite swing)
    glPushMatrix()
    glTranslatef(12, 0, 10)
    glRotatef(base_arm_bias - arm_swing, 1, 0, 0)  # opposite phase
    glRotatef(90, 1, 0, 0)  # point cylinder down
    glColor3f(1, 0.8, 0.6)
    gluCylinder(gluNewQuadric(), 2, 2, 12, 8, 8)
    glPopMatrix()
    # ---- /ARMS ----
    
    # ---- LEGS (fixed, pointing downward) ----
    hip_z = -13.5          # torso half-height below origin
    leg_height = 14.0      # ends near ground
    
    # Left Leg
    glPushMatrix()
    glTranslatef(-5, 0, hip_z)
    glRotatef(leg_stride, 1, 0, 0)  # stride
    glRotatef(180, 1, 0, 0)         # point cylinder toward -Z (down)
    glColor3f(0.2, 0.2, 0.8)        # Dark blue pants
    gluCylinder(gluNewQuadric(), 3, 3, leg_height, 8, 8)
    glPopMatrix()
    
    # Right Leg (opposite stride)
    glPushMatrix()
    glTranslatef(5, 0, hip_z)
    glRotatef(-leg_stride, 1, 0, 0)
    glRotatef(180, 1, 0, 0)
    glColor3f(0.2, 0.2, 0.8)
    gluCylinder(gluNewQuadric(), 3, 3, leg_height, 8, 8)
    glPopMatrix()

    # Feet
    foot_z = hip_z - leg_height - 1.0  # tiny offset to avoid z-fighting
    # Left Foot
    glPushMatrix()
    glTranslatef(-5, 2, foot_z)
    glColor3f(0.1, 0.1, 0.1)
    glScalef(0.8, 1.2, 0.4)
    glutSolidCube(6)
    glPopMatrix()
    # Right Foot
    glPushMatrix()
    glTranslatef(5, 2, foot_z)
    glColor3f(0.1, 0.1, 0.1)
    glScalef(0.8, 1.2, 0.4)
    glutSolidCube(6)
    glPopMatrix()
    # ---- /LEGS ----
    
    glPopMatrix()

def draw_coin(x, y, z):
    """Draw a yellow sphere representing a coin"""
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(1, 1, 0)  # Yellow color
    glutSolidSphere(10, 10, 10)  # Draw the coin
    glPopMatrix()

def draw_obstacle(x, y, z):
    """Draw a red cube representing an obstacle"""
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(1, 0, 0)  # Red color
    glutSolidCube(20)  # Draw the obstacle
    glPopMatrix()

def draw_coins():
    """Draw all active coins"""
    for coin in coins:
        draw_coin(coin['x'], coin['y'], coin['z'])

def draw_obstacles():
    """Draw all active obstacles"""
    for obstacle in obstacles:
        draw_obstacle(obstacle['x'], obstacle['y'], obstacle['z'])

def is_position_valid(new_x, new_y, is_obstacle=False):
    """Check if a new position is valid (doesn't overlap with existing objects)"""
    # Check against obstacles
    for obstacle in obstacles:
        if abs(obstacle['y'] - new_y) < min_vertical_gap and obstacle['x'] == new_x:
            return False
    
    # Check against coins (if placing an obstacle)
    if is_obstacle:
        for coin in coins:
            if abs(coin['y'] - new_y) < min_vertical_gap and coin['x'] == new_x:
                return False
    
    return True

def spawn_coin():
    """Spawn a new coin at a random position in front of the player"""
    attempts = 0
    max_attempts = 10  # Prevent infinite loop
    
    while attempts < max_attempts:
        lane = random.randint(0, 2)  # Random lane (0=left, 1=center, 2=right)
        x = LANE_POSITIONS[lane]
        y = runner_z_pos + 300 + random.randint(0, 200)  # Spawn ahead of player
        z = 20  # Same height as runner
        
        # Check if position is valid
        if is_position_valid(x, y):
            coins.append({'x': x, 'y': y, 'z': z})
            return
        
        attempts += 1

def spawn_obstacle():
    """Spawn obstacles in front of the player, ensuring not all lanes are blocked and with proper spacing"""
    attempts = 0
    max_attempts = 10  # Prevent infinite loop
    
    while attempts < max_attempts:
        # Choose 1 or 2 lanes to spawn obstacles (never all 3)
        num_obstacles = random.randint(1, 2)
        obstacle_lanes = random.sample([0, 1, 2], num_obstacles)
        
        valid_placement = True
        new_obstacles = []
        
        for lane in obstacle_lanes:
            x = LANE_POSITIONS[lane]
            y = runner_z_pos + 400 + random.randint(0, 100)  # Spawn ahead of player
            z = 10  # Height of obstacle
            
            # Check if position is valid
            if not is_position_valid(x, y, is_obstacle=True):
                valid_placement = False
                break
                
            new_obstacles.append({'x': x, 'y': y, 'z': z})
        
        # If all obstacles are valid, add them to the game
        if valid_placement and new_obstacles:
            obstacles.extend(new_obstacles)
            return
        
        attempts += 1

def update_coins():
    """Update coin positions and check for collection"""
    global points, coins
    
    # Move coins toward the player (simulate player moving forward)
    for coin in coins[:]:
        coin['y'] -= game_speed
        
        # Check if coin is behind the player
        if coin['y'] < runner_z_pos - 50:
            coins.remove(coin)
            continue
            
        # Check for collection
        distance = math.sqrt(
            (coin['x'] - runner_x_pos)**2 + 
            (coin['y'] - runner_z_pos)**2 + 
            (coin['z'] - 20)**2
        )
        
        if distance < coin_collection_distance:
            coins.remove(coin)  # Remove coin instantly
            points += 1
            print(f"Coin collected! Total points: {points}")

def update_obstacles():
    """Update obstacle positions and check for collisions"""
    global game_running, obstacles
    
    # Move obstacles toward the player (simulate player moving forward)
    for obstacle in obstacles[:]:
        obstacle['y'] -= game_speed
        
        # Check if obstacle is behind the player
        if obstacle['y'] < runner_z_pos - 50:
            obstacles.remove(obstacle)
            continue
            
        # Check for collision
        distance = math.sqrt(
            (obstacle['x'] - runner_x_pos)**2 + 
            (obstacle['y'] - runner_z_pos)**2 + 
            (obstacle['z'] - 10)**2
        )
        
        if distance < obstacle_collision_distance:
            game_running = False
            print(f"Game Over! Final points: {points}")
            break

def draw_ground():
    """Draw ground/hills for background"""
    # Ground plane
    glColor3f(0.2, 0.8, 0.2)  # Green ground
    glBegin(GL_QUADS)
    
    ground_size = 1000
    glVertex3f(-ground_size, -ground_size, -5)
    glVertex3f(ground_size, -ground_size, -5)
    glVertex3f(ground_size, ground_size, -5)
    glVertex3f(-ground_size, ground_size, -5)
    
    glEnd()
    
    # Side barriers/walls
    glColor3f(0.6, 0.3, 0.1)  # Brown barriers
    barrier_height = 50
    track_width = LANE_WIDTH * 3
    
    # Left barrier
    glBegin(GL_QUADS)
    glVertex3f(-track_width/2 - 20, -1000, 0)
    glVertex3f(-track_width/2 - 20, 1000, 0)
    glVertex3f(-track_width/2 - 20, 1000, barrier_height)
    glVertex3f(-track_width/2 - 20, -1000, barrier_height)
    glEnd()
    
    # Right barrier
    glBegin(GL_QUADS)
    glVertex3f(track_width/2 + 20, -1000, 0)
    glVertex3f(track_width/2 + 20, 1000, 0)
    glVertex3f(track_width/2 + 20, 1000, barrier_height)
    glVertex3f(track_width/2 + 20, -1000, barrier_height)
    glEnd()

def draw_shapes():
    """Draw all game objects"""
    draw_ground()
    draw_track()
    draw_runner()
    draw_coins()
    draw_obstacles()

def update_game():
    """Update game logic"""
    global runner_x_pos, runner_target_x, track_offset, score, distance_covered, game_speed, start_time
    global coin_spawn_timer, coins, obstacle_spawn_timer, obstacles
    
    if not game_running or start_time is None:
        return
    
    # Calculate distance based on time (1 meter per second)
    current_time = time.time()
    distance_covered = current_time - start_time
    
    # Smooth lane transition with better interpolation
    diff = runner_target_x - runner_x_pos
    if abs(diff) > 0.5:
        runner_x_pos += diff * 0.15  # Smoother interpolation
    else:
        runner_x_pos = runner_target_x
    
    # Move track (creates running effect)
    track_offset += game_speed
    
    # Much more gradual speed increase (every 20 seconds instead of 10)
    speed_increase = min(distance_covered / 20.0, max_speed - base_speed)  # Increase every 20 seconds
    game_speed = base_speed + speed_increase * 0.5  # Even slower speed increase rate
    
    # Increase score over time
    score += 1
    
    # Update coins and obstacles
    update_coins()
    update_obstacles()
    
    # Spawn new coins periodically
    coin_spawn_timer += 0.016  # Assuming ~60fps
    if coin_spawn_timer >= coin_spawn_interval:
        spawn_coin()
        coin_spawn_timer = 0
    
    # Spawn new obstacles periodically
    obstacle_spawn_timer += 0.016  # Assuming ~60fps
    if obstacle_spawn_timer >= obstacle_spawn_interval:
        spawn_obstacle()
        obstacle_spawn_timer = 0

def keyboardListener(key, x, y):
    """
    Handles keyboard inputs for player movement, camera updates, reset, and pause toggle.
    """
    global game_running, current_lane, runner_target_x, start_time, pause_start
    
    # Reset the game if R key is pressed
    if key == b'r':
        reset_game()
        print("Game Reset!")
        return

    # SPACE to pause/resume
    if key == b' ':
        if game_running:
            # Pause: stop updates and record when pause began
            game_running = False
            pause_start = time.time()
            print("Paused")
        else:
            # Resume: adjust start_time so distance excludes pause duration
            if pause_start is not None and start_time is not None:
                paused_duration = time.time() - pause_start
                start_time += paused_duration
            game_running = True
            pause_start = None
            print("Resumed")

def specialKeyListener(key, x, y):
    """
    Handles special key inputs (arrow keys) for adjusting the camera angle and height,
    and lane switching.
    """
    global camera_pos, current_lane, runner_target_x, runner_x_pos
    cx, cy, cz = camera_pos
    
    # Move camera up (UP arrow key)
    if key == GLUT_KEY_UP:
        cz += 5
    
    # Move camera down (DOWN arrow key)
    if key == GLUT_KEY_DOWN:
        cz -= 5
    
    # moving to left lane (LEFT arrow key)
    if key == GLUT_KEY_LEFT:
        # Switch to left lane with debouncing
        if current_lane > 0 and abs(runner_x_pos - runner_target_x) < 5:
            current_lane -= 1
            runner_target_x = LANE_POSITIONS[current_lane]
            print(f"Switching to lane {current_lane}")
    
    # moving to right lane (RIGHT arrow key)
    if key == GLUT_KEY_RIGHT:
        # Switch to right lane with debouncing
        if current_lane < 2 and abs(runner_x_pos - runner_target_x) < 5:
            current_lane += 1
            runner_target_x = LANE_POSITIONS[current_lane]
            print(f"Switching to lane {current_lane}")

    camera_pos = (cx, cy, cz)


def mouseListener(button, state, x, y):
    """
    Handles mouse inputs for future features (e.g., jump or camera toggle).
    """
    global first_person_view

    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        # Toggle between first-person and third-person view
        first_person_view = not first_person_view
        if first_person_view:
            print("Switched to First-Person View")
        else:
            print("Switched to Third-Person View")


def setupCamera():
    """
    Configures the camera's projection and view settings.
    Uses a perspective projection and positions the camera to look at the target.
    """
    glMatrixMode(GL_PROJECTION)  # Switch to projection matrix mode
    glLoadIdentity()  # Reset the projection matrix
    # Set up a perspective projection (field of view, aspect ratio, near clip, far clip)
    gluPerspective(fovY, 1.25, 0.1, 1500)  # aspect ratio matches viewport 1000x800
    glMatrixMode(GL_MODELVIEW)  # Switch to model-view matrix mode
    glLoadIdentity()  # Reset the model-view matrix

    # Extract camera position and follow the runner smoothly
    cam_x, cam_y, cam_z = camera_pos

    if first_person_view:
        # In first-person view, the camera will follow the runner's position exactly
        camera_x = runner_x_pos  # Directly behind the runner
        camera_y = runner_z_pos + 10  # Height of the camera
        camera_z = 10  # Just slightly in front of the runner to simulate first-person view
    else:
        # In third-person view, the camera follows with a slight offset
        camera_x = runner_x_pos * 0.3  # Reduced camera follow for less jitter
        camera_y = runner_z_pos + cam_y
        camera_z = cam_z

    # Position the camera and set its orientation
    gluLookAt(camera_x, camera_y, camera_z,  # Camera position
              runner_x_pos * 0.5, runner_z_pos + 100, 10,  # Look slightly ahead of runner
              0, 0, 1)  # Up vector (z-axis)


def idle():
    """
    Idle function that runs continuously:
    - Triggers screen redraw for real-time updates.
    """
    update_game()  # Update game state
    glutPostRedisplay()  # Ensure the screen updates with the latest changes

def showScreen():
    """
    Display function to render the game scene:
    - Clears the screen and sets up the camera.
    - Draws everything on the screen.
    """
    # Clear color and depth buffers
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()  # Reset modelview matrix
    glViewport(0, 0, 1000, 800)  # Set viewport size
    
    # Enable depth testing for 3D
    glEnable(GL_DEPTH_TEST)

    setupCamera()  # Configure camera perspective

    draw_shapes()  # Draw all game objects

    # Disable depth testing for UI text rendering
    glDisable(GL_DEPTH_TEST)
    
    # HUD
    draw_text(10, 670, f"Distance Travelled: {distance_covered:.1f}m")
    draw_text(10, 640, f"Points: {points}")
    draw_text(10, 610, f"Press 'r' to restart")
    draw_text(10, 580, f"Press SPACE to pause/resume")
    
    if not game_running:
        # Big PAUSED indicator
        glColor3f(1, 1, 1)
        draw_text(500, 400, "PAUSED", GLUT_BITMAP_TIMES_ROMAN_24)
        
        # Game over message if not paused
        if pause_start is None:
            draw_text(450, 350, "GAME OVER", GLUT_BITMAP_TIMES_ROMAN_24)
            draw_text(430, 300, f"Final Points: {points}", GLUT_BITMAP_TIMES_ROMAN_24)

    # Re-enable depth testing
    glEnable(GL_DEPTH_TEST)

    # Swap buffers for smooth rendering (double buffering)
    glutSwapBuffers()

# Main function to set up OpenGL window and loop
def main():
    global start_time
    
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)  # Double buffering, RGB color, depth test
    glutInitWindowSize(1000, 800)  # Window size
    glutInitWindowPosition(0, 0)  # Window position
    glutCreateWindow(b"3D Runner Game")  # Create the window

    glutDisplayFunc(showScreen)      # Register display function
    glutKeyboardFunc(keyboardListener)  # Register keyboard listener
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)  # Register the idle function for continuous updates
    
    # Set clear color to sky blue
    glClearColor(0.5, 0.8, 1.0, 1.0)
    
    # Initialize start time
    start_time = time.time()

    glutMainLoop()  # Enter the GLUT main loop

if __name__ == "__main__":
    main()