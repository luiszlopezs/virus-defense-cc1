import random

# CONSTANTS:
HEALTHY = 0
VIRUS = 1
PATCHED = 2


class Grid:
    def __init__(self, rows: int, cols: int):
        """
        Initializes the game board as a matrix filled with empty cells.

        Parameters:
        rows (int): Number of rows in the grid.
        cols (int): Number of columns in the grid.

        Cell values:
        0 = Empty
        1 = Virus
        2 = Patched node (protected zone)
        """
        self.rows = rows
        self.cols = cols
        self.matrix = [[HEALTHY for _ in range(cols)] for _ in range(rows)]

    def is_inside(self, row: int, col: int) -> bool:
        """
        Checks if a given position is inside the board limits.
        """
        return 0 <= row < self.rows and 0 <= col < self.cols

    def set_cell(self, row: int, col: int, value: int):
        """
        Assigns a value to a specific cell if it is inside the board.
        """
        if self.is_inside(row, col):
            self.matrix[row][col] = value

    def get_cell(self, row: int, col: int) -> int:
        """
        Returns the value of a cell. If the position is outside,
        returns -1.
        """
        if self.is_inside(row, col):
            return self.matrix[row][col]
        return -1

    def get_neighbors(self, row: int, col: int) -> list:
        """
        Returns a list of valid neighboring positions (up, down,
        left, right) within the board.
        """
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        neighbors = []

        for drow, dcol in directions:# delta row and delta column
            nrow, ncol = row + drow, col + dcol# new row and new column
            if self.is_inside(nrow, ncol):
                neighbors.append((nrow, ncol))

        return neighbors

    def generate_safe_path(self):
        """
        Generates a guaranteed valid path from the start (0,0) to 
        the goal (bottom-right corner).

        The path only moves right or down to ensure it always reaches 
        the goal.
        This path will later be protected from virus placement.

        This is to ensure that the game always has a solution.
        """
        i, j = 0, 0
        path = [(i, j)]

        while (i, j) != (self.rows - 1, self.cols - 1):
            options = []
            if i + 1 < self.rows:
                options.append((i + 1, j))
            if j + 1 < self.cols:
                options.append((i, j + 1))

            i, j = random.choice(options)
            path.append((i, j))

        return path
    def spawn_initial_virus_cluster(self, expansion_steps: int, path: list[tuple[int, int]]):
        """
        Selects a single random starting point (Patient Zero) outside the safe path,
        and expands it for a given number of steps to create a dense initial virus cluster.
        
        This allows the Greedy patcher to effectively find high-risk boundaries and
        the Backtracking pathfinder to map routes around a unified threat.
        """
        path_set = set(path)
        patient_zero = None

        # Find a single valid random spot for Patient Zero:
        while patient_zero is None:
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)

            if (r, c) not in path_set and self.get_cell(r, c) == HEALTHY:
                patient_zero = (r, c)
                self.set_cell(r, c, VIRUS)

        # Grow the cluster locally before the game session starts:
        for _ in range(expansion_steps):
            self.expand_virus()

    def spawn_random_protected_zones(self, count: int, path):
        """
        Randomly places protected zones along the safe path.

        Protected zones can later be used to influence
        algorithm decisions (e.g., safer paths).
        """
        placed = 0

        while placed < count:
            r, c = random.choice(path)

            if self.get_cell(r, c) == HEALTHY:
                self.set_cell(r, c, PATCHED)
                placed += 1
                
    def expand_virus(self, infection_chance: float = 0.35):
        """
        Spreads the virus into adjacent healthy nodes based on a probability check.
        PATCHED nodes act as physical barriers and block this expansion.
        
        Parameters:
        infection_chance (float): Value between 0.0 and 1.0 (e.g., 0.35 = 35% chance to spread).
        """
        infected_nodes = []
        
        # Locate all current virus outbreak positions on the board:
        for r in range(self.rows):
            for c in range(self.cols):
                if self.matrix[r][c] == VIRUS:
                    infected_nodes.append((r, c))
        
        # Contaminate orthogonal healthy neighbors based on probability:
        for r, c in infected_nodes:
            for nr, nc in self.get_neighbors(r, c):
                if self.matrix[nr][nc] == HEALTHY:
                    # Only infect if the random roll is less than the chance threshold
                    if random.random() < infection_chance:
                        self.matrix[nr][nc] = VIRUS