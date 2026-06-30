#!/usr/bin/env python3
import pygame
import sys
import os
import time
import warnings

# Suppress pkg_resources deprecation warning from dependencies
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated as an API.*")

def install_reopen_handler():
    """Installs the event handler for the 'reopen' application event on macOS."""
    if sys.platform != 'darwin':
        return
        
    try:
        import ctypes
        from ctypes.util import find_library

        EventHandlerProcPtr = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long)

        def _handle_reopen_app_event(event, reply, ref_con):
            return 0

        _reopen_handler_c = EventHandlerProcPtr(_handle_reopen_app_event)
        app_services = ctypes.cdll.LoadLibrary(find_library('ApplicationServices'))
        
        kCoreEventClass = int.from_bytes(b'aevt', 'big')
        kAEReopenApplication = int.from_bytes(b'rapp', 'big')
        kAEGotRequiredParams = int.from_bytes(b'oapp', 'big')

        app_services.AEInstallEventHandler(kCoreEventClass, kAEReopenApplication, _reopen_handler_c, 0, False)
        app_services.AEInstallEventHandler(kCoreEventClass, kAEGotRequiredParams, _reopen_handler_c, 0, False)

    except (ImportError, OSError, AttributeError):
        pass

# Add project root to sys.path to allow imports when run as a standalone script
if __name__ == "__main__" and not __package__:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.font_utils import safe_sys_font

DEFAULT_UI_FONT = "alibabapuhuiti"

def get_window_icon_path():
    """Return the shared app icon path for source and frozen builds."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, 'ui', 'img', 'drone.png')


def set_window_icon():
    """Apply the shared app icon to the startup dialog window."""
    try:
        icon_path = get_window_icon_path()
        if os.path.exists(icon_path):
            icon = pygame.image.load(icon_path)
            pygame.display.set_icon(icon)
    except Exception as e:
        print(f"Warning: Could not load window icon: {e}", file=sys.stderr)


def show_startup_dialog():
    """Show a Pygame dialog asking to start the UI.
    Prints 'YES', 'NO', or 'CANCEL' to stdout.
    """
    # Fix for macOS dock icon crash
    if sys.platform == 'darwin':
        install_reopen_handler()

    pygame.init()
    width, height = 540, 250
    
    # Center the window
    os.environ['SDL_VIDEO_CENTERED'] = '1'

    set_window_icon()
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("MultiUAV-Plat Server System")
    
    # Try to force focus on macOS
    if sys.platform == 'darwin':
        try:
            os.system('''/usr/bin/osascript -e 'tell app "System Events" to set frontmost of every process whose unix id is %d to true' ''' % os.getpid())
        except:
            pass
    
    font_title = safe_sys_font(DEFAULT_UI_FONT, 24, bold=True)
    font_msg = safe_sys_font(DEFAULT_UI_FONT, 18)
    font_btn = safe_sys_font(DEFAULT_UI_FONT, 20, bold=True)
    
    # Colors
    BG = (245, 245, 250)
    BTN_BG = (225, 230, 235)
    BTN_HOVER = (210, 215, 220)
    BTN_BORDER = (180, 190, 200)
    TEXT_COL = (40, 44, 52)
    ACCENT_COL = (0, 122, 255)
    
    btn_yes = pygame.Rect(120, 160, 120, 45)
    btn_no = pygame.Rect(300, 160, 120, 45)
    
    running = True
    result = "CANCEL" # Default
    
    clock = pygame.time.Clock()
    
    while running:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                result = "CANCEL"
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn_yes.collidepoint(event.pos):
                    result = "YES"
                    running = False
                elif btn_no.collidepoint(event.pos):
                    result = "NO"
                    running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    result = "YES"
                    running = False
                elif event.key in (pygame.K_n, pygame.K_ESCAPE, pygame.K_RETURN):
                    result = "NO"
                    running = False

        screen.fill(BG)
        
        # Decorative top bar
        pygame.draw.rect(screen, ACCENT_COL, (0, 0, width, 5))
        
        # Text
        title_surf = font_title.render("Start User Interface?", True, TEXT_COL)
        msg1_surf = font_msg.render("The API server is running in the background.", True, TEXT_COL)
        msg2_surf = font_msg.render("Would you like to open the graphical dashboard?", True, TEXT_COL)
        
        screen.blit(title_surf, (width//2 - title_surf.get_width()//2, 40))
        screen.blit(msg1_surf, (width//2 - msg1_surf.get_width()//2, 85))
        screen.blit(msg2_surf, (width//2 - msg2_surf.get_width()//2, 110))
        
        # Buttons
        yes_hover = btn_yes.collidepoint(mouse_pos)
        no_hover = btn_no.collidepoint(mouse_pos)
        
        # Yes Button
        pygame.draw.rect(screen, BTN_HOVER if yes_hover else BTN_BG, btn_yes, border_radius=8)
        pygame.draw.rect(screen, ACCENT_COL if yes_hover else BTN_BORDER, btn_yes, 2, border_radius=8)
        
        # No Button (Default - highlighted)
        pygame.draw.rect(screen, BTN_HOVER if no_hover else BTN_BG, btn_no, border_radius=8)
        pygame.draw.rect(screen, ACCENT_COL, btn_no, 2, border_radius=8)
        
        yes_txt = font_btn.render("Yes", True, ACCENT_COL if yes_hover else TEXT_COL)
        no_txt = font_btn.render("No", True, ACCENT_COL if no_hover else TEXT_COL)
        
        screen.blit(yes_txt, (btn_yes.centerx - yes_txt.get_width()//2, btn_yes.centery - yes_txt.get_height()//2))
        screen.blit(no_txt, (btn_no.centerx - no_txt.get_width()//2, btn_no.centery - no_txt.get_height()//2))
        
        pygame.display.flip()
        clock.tick(60)

    pygame.display.quit()
    pygame.quit()
    
    # Print result to stdout for parent process to read
    print(result)

if __name__ == "__main__":
    show_startup_dialog()
