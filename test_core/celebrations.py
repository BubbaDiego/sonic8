from rich.console import Console
from pyfiglet import Figlet
# import chime
# import beepy
# from asciimatics.effects import Stars
# from asciimatics.scene import Scene
# from asciimatics.screen import Screen

console = Console()

def celebrate_top_tier(grade):
    figlet = Figlet(font="slant")
    console.print(f"[bold magenta]{figlet.renderText(grade)}[/bold magenta]")
    console.print(":tada: [bold green]Outstanding![/bold green] :tada:")

    # chime.success()  # Temporarily disabled
    # beepy.beep(sound='success')  # Temporarily disabled

    # Temporarily disabled terminal animation to prevent hang
    # def fireworks(screen):
    #     effects = [Stars(screen, (screen.width + screen.height) // 2)]
    #     screen.play([Scene(effects, duration=50)])
    # Screen.wrapper(fireworks)

def celebrate_mid_tier(grade):
    color = "cyan" if "B" in grade else "yellow"
    emoji = "👍" if "+" in grade else "🙂" if "-" in grade else "⭐"
    console.print(f"[bold {color}]Grade {grade} – Good Job![/bold {color}] {emoji}")

    # beepy.beep(sound='coin')  # Temporarily disabled

def alert_low_tier(grade):
    console.print(f"[bold red blink]Grade {grade} – Needs Improvement[/bold red blink] ❌")

    # beepy.beep(sound='error')  # Temporarily disabled

def celebrate_grade(grade):
    if grade in ["A+", "A", "A-"]:
        celebrate_top_tier(grade)
    elif grade in ["B+", "B", "B-", "C+", "C", "C-"]:
        celebrate_mid_tier(grade)
    else:
        alert_low_tier(grade)
