class Character:
    def __init__(self, fname: str, lname: str, age: int):
        self.fname = fname
        self.lname = lname
        self.age = age

    def __repr__(self):
        return f"{self.fname.capitalize()} {self.lname.capitalize()}"
