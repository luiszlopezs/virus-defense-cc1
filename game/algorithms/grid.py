import random

# CONSTANTS:
VACIO = 0
VIRUS = 1
PROTEGIDO = 2


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
        2 = Protected zone
        """
        self.rows = rows
        self.cols = cols
        self.matrix = [[VACIO for _ in range(cols)] for _ in range(rows)]

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

    def spawn_random_viruses(self, count: int, path): #generate viruses in random positions, but not in the path
        """
        Randomly places a given number of viruses on the board.

        Viruses are NOT placed on the safe path to guarantee
        that at least one valid solution exists.
        """
        path_set = set(path)
        placed = 0

        while placed < count:
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)

            if (r, c) in path_set:
                continue

            if self.get_cell(r, c) == VACIO:
                self.set_cell(r, c, VIRUS)
                placed += 1

    def spawn_random_protected_zones(self, count: int, path):
        """
        Randomly places protected zones along the safe path.

        Protected zones can later be used to influence
        algorithm decisions (e.g., safer paths).
        """
        placed = 0

        while placed < count:
            r, c = random.choice(path)

            if self.get_cell(r, c) == VACIO:
                self.set_cell(r, c, PROTEGIDO)
                placed += 1