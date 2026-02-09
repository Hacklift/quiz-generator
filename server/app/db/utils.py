import bcrypt



def is_valid_password(plain_password: str, hashed_password: str) -> bool:

    return bcrypt.checkpw(

        plain_password.encode("utf-8"), hashed_password.encode("utf-8")

    )



def hash_password(password: str) -> str:

    salt = bcrypt.gensalt()

    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


