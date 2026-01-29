import bcrypt

from src.database import User
from src.logger import log_function


class UserService:
    """Сервис для управления пользователями и аутентификацией."""

    @staticmethod
    @log_function
    async def get_user_by_username(username: str) -> User | None:
        """Возвращает пользователя по имени пользователя."""
        return await User.get_or_none(username=username)

    @staticmethod
    async def create_user(
        username: str, password: str, is_superuser: bool = False
    ) -> User:
        """Создает нового пользователя с хешированным паролем."""
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        user = await User.create(
            username=username, password_hash=password_hash, is_superuser=is_superuser
        )
        return user

    @staticmethod
    async def verify_password(password: str, password_hash: str) -> bool:
        """Проверяет соответствие пароля его хешу."""
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    @staticmethod
    @log_function
    async def verify_superuser(username: str, password: str) -> bool:
        """Проверяет, является ли пользователь суперпользователем и верен ли пароль."""
        user = await UserService.get_user_by_username(username)
        if not user:
            return False
        if not user.is_superuser:
            return False
        return await UserService.verify_password(password, user.password_hash)

    @staticmethod
    async def update_password(user: User, password: str) -> None:
        """Обновляет пароль пользователя, хешируя его."""
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        user.password_hash = password_hash
        await user.save()


