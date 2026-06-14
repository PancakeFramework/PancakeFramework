ico = """

                                .-.
                                : :.-.
.---.  .--.  ,-.,-. .--.  .--.  : `'.' .--.
: .; `' .; ; : ,. :'  ..'' .; ; : . `.' '_.'
: ._.'`.__,_;:_;:_;`.__.'`.__,_;:_;:_;`.__.'
: :
:_;                           
"""

def print_ico():
    print(ico)

def print_cover():
    import os
    cover_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cover")
    with open(cover_path, "r", encoding="utf-8") as f:
        print(f.read())
