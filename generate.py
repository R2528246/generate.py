import sys

from crossword import *


class CrosswordCreator:

    def __init__(self, crossword):
        """Create a new crossword puzzle generator."""
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """Return a 2D array of letters for the given assignment."""
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]

        for variable, word in assignment.items():
            for k in range(len(word)):
                i = variable.i + (k if variable.direction == Variable.DOWN else 0)
                j = variable.j + (k if variable.direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]

        return letters

    def print(self, assignment):
        """Print the crossword assignment to the terminal."""
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """Save an image of the crossword assignment."""
        from PIL import Image, ImageDraw, ImageFont

        cell_size = 100
        cell_border = 2
        grid = self.letter_grid(assignment)
        image = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(image)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if grid[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), grid[i][j], font=font)
                        draw.text(
                            (rect[0][0] + (cell_size - w) / 2,
                             rect[0][1] + (cell_size - h) / 2 - 10),
                            grid[i][j],
                            fill="black",
                            font=font
                        )

        image.save(filename)

    def solve(self):
        """Enforce initial consistency and search for a solution."""
        self.enforce_node_consistency()
        if not self.ac3():
            return None
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """Remove words whose lengths do not match their variables."""
        for var in self.crossword.variables:
            self.domains[var] = {
                word for word in self.domains[var]
                if len(word) == var.length
            }

    def revise(self, x, y):
        """Make the domain of x consistent with the domain of y."""
        overlap = self.crossword.overlaps[x, y]
        if overlap is None:
            return False

        i, j = overlap
        revised = False

        for word_x in set(self.domains[x]):
            if not any(word_x[i] == word_y[j] for word_y in self.domains[y]):
                self.domains[x].remove(word_x)
                revised = True

        return revised

    def ac3(self, arcs=None):
        """Enforce arc consistency using the AC-3 algorithm."""
        if any(not domain for domain in self.domains.values()):
            return False

        if arcs is None:
            queue = [
                (x, y)
                for x in self.crossword.variables
                for y in self.crossword.neighbors(x)
            ]
        else:
            queue = list(arcs)

        while queue:
            x, y = queue.pop(0)

            if self.revise(x, y):
                if not self.domains[x]:
                    return False

                for z in self.crossword.neighbors(x):
                    if z != y:
                        queue.append((z, x))

        return True

    def assignment_complete(self, assignment):
        """Return True if every crossword variable has a value."""
        return all(var in assignment for var in self.crossword.variables)

    def consistent(self, assignment):
        """Check word lengths, uniqueness, and all overlap constraints."""
        words = list(assignment.values())
        if len(words) != len(set(words)):
            return False

        for var, word in assignment.items():
            if len(word) != var.length:
                return False

            for neighbor in self.crossword.neighbors(var):
                if neighbor in assignment:
                    i, j = self.crossword.overlaps[var, neighbor]
                    if word[i] != assignment[neighbor][j]:
                        return False

        return True

    def order_domain_values(self, var, assignment):
        """Order values by least-constraining-value heuristic."""
        def ruled_out_count(word):
            count = 0
            for neighbor in self.crossword.neighbors(var):
                if neighbor in assignment:
                    continue

                i, j = self.crossword.overlaps[var, neighbor]
                count += sum(
                    word[i] != neighbor_word[j]
                    for neighbor_word in self.domains[neighbor]
                )
            return count

        return sorted(self.domains[var], key=ruled_out_count)

    def select_unassigned_variable(self, assignment):
        """Choose an unassigned variable using MRV and degree heuristics."""
        unassigned = [
            var for var in self.crossword.variables
            if var not in assignment
        ]

        return min(
            unassigned,
            key=lambda var: (
                len(self.domains[var]),
                -sum(
                    neighbor not in assignment
                    for neighbor in self.crossword.neighbors(var)
                )
            )
        )

    def backtrack(self, assignment):
        """Use recursive backtracking to find a complete assignment."""
        if self.assignment_complete(assignment):
            return assignment

        var = self.select_unassigned_variable(assignment)

        for value in self.order_domain_values(var, assignment):
            new_assignment = assignment.copy()
            new_assignment[var] = value

            if self.consistent(new_assignment):
                result = self.backtrack(new_assignment)
                if result is not None:
                    return result

        return None


def main():
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
