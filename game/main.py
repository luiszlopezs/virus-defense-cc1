from algorithms.grid import Grid, VIRUS, PROTEGIDO
from algorithms.greedy import greedy_suggestion
from algorithms.backtracking import backtracking_suggestion

# =========================
# DISPLAY
# =========================
def display(grid, player):
    """
    Displays the board in the console.

    Symbols:
    J = Player
    X = Virus
    P = Protected zone
    F = Goal
    . = Empty
    """
    for i in range(grid.rows):
        row = ""
        for j in range(grid.cols):
            if (i, j) == player:
                row += "J "
            elif grid.get_cell(i, j) == VIRUS:
                row += "X "
            elif grid.get_cell(i, j) == PROTEGIDO:
                row += "P "
            elif (i, j) == (grid.rows - 1, grid.cols - 1):
                row += "F "
            else:
                row += ". "
        print(row)

# =========================
# GAME LOOP (Keep playing until the game is over)
# =========================
def play(grid):
    """
    Main interactive loop of the game.

    The player selects an algorithm (greedy or backtracking),
    and at each step receives a suggested move (to be implemented later).
    The player can choose to follow the suggestion or move manually.
    """
    player = (0, 0)

    print("\nChoose algorithm:")
    print("1. Greedy")
    print("2. Backtracking")

    option = input("Option: ")

    if option == "1":
        method = "greedy"
    elif option == "2":
        method = "backtracking"
    else:
        print("Invalid option, defaulting to manual mode")
        method = "none"

    while True:
        print("\n" + "="*40)
        display(grid, player)

        neighbors = grid.get_neighbors(player[0], player[1])

        print("\nAvailable moves:")
        for idx, (r, c) in enumerate(neighbors):
            print(f"{idx}: ({r},{c})")

        # Placeholder for algorithm suggestion
        if method == "greedy":
            suggestion = greedy_suggestion(grid, player)
        elif method == "backtracking":
            suggestion = backtracking_suggestion(grid, player)
        else:
            suggestion = None

        print(f"\nSuggested move ({method}): {suggestion}")

        print("\n1. Follow suggestion")
        print("2. Choose manually")

        decision = input("Option: ")

        if decision == "1" and suggestion:
            player = suggestion
        else:
            try:
                choice = int(input("Choose index: "))
                player = neighbors[choice]
            except (ValueError, IndexError):
                print("Invalid input, try again")
                continue

        cell = grid.get_cell(player[0], player[1])

        if cell == VIRUS:
            print("\nYou stepped on a virus. GAME OVER.")
            display(grid, player)
            break

        if player == (grid.rows - 1, grid.cols - 1):
            print("\nYou reached the goal. YOU WIN.")
            display(grid, player)
            break


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    """
    Entry point of the program.

    Initializes the board, generates a guaranteed safe path,
    places viruses and protected zones, and starts the game.
    """
    grid = Grid(12, 12)

    path = grid.generate_safe_path()

    grid.spawn_random_viruses(24, path)
    grid.spawn_random_protected_zones(10, path)

    play(grid)