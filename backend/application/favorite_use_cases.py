from infrastructure.database.repositories.user_repository import (
    get_user_favorites,
    add_favorite as repo_add_favorite,
    remove_favorite as repo_remove_favorite,
)


def get_favorites(user_id):
    return get_user_favorites(user_id)


def add_favorite(user_id, cca3):
    if not cca3:
        return False, "Se requiere cca3 del país"

    repo_add_favorite(user_id, cca3)
    return True, None


def remove_favorite(user_id, cca3):
    repo_remove_favorite(user_id, cca3)
    return True, None
