from tortoise import fields, models

class User(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=255, unique=True)
    password_hash = fields.CharField(max_length=255)
    is_superuser = fields.BooleanField(default=False)

    class Meta:
        table = "users"

class Setting(models.Model):
    key = fields.CharField(max_length=255, pk=True)
    value = fields.TextField()

    class Meta:
        table = "settings"

class ChatMessage(models.Model):
    """Модель для хранения сообщений чата."""
    id = fields.IntField(pk=True)
    chat_id = fields.BigIntField(index=True)
    role = fields.CharField(max_length=50)  # user, assistant, system
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_messages"

class LLMConnection(models.Model):
    """Модель для хранения параметров подключения к LLM провайдерам."""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    provider = fields.CharField(max_length=50, default="openrouter")
    api_key = fields.TextField()
    base_url = fields.CharField(max_length=255, null=True)
    model_name = fields.CharField(max_length=255)
    is_active = fields.BooleanField(default=False)

    class Meta:
        table = "llm_connections"

    def __str__(self) -> str:
        return f"{self.name} ({self.provider})"

class LLMPrompt(models.Model):
    """Модель для хранения системных промптов для конкретных подключений."""
    id = fields.IntField(pk=True)
    connection = fields.ForeignKeyField("models.LLMConnection", related_name="prompts")
    name = fields.CharField(max_length=255)
    content = fields.TextField()
    is_active = fields.BooleanField(default=False)

    class Meta:
        table = "llm_prompts"

    def __str__(self) -> str:
        return f"{self.name} [{self.connection.name}]"


class AllowedChat(models.Model):
    """Модель для хранения разрешенных чатов."""
    id = fields.IntField(pk=True)
    chat_id = fields.BigIntField(unique=True, index=True)
    title = fields.CharField(max_length=255, null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "allowed_chats"

    def __str__(self) -> str:
        return f"{self.title} ({self.chat_id})"
