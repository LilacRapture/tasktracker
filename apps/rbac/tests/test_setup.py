def test_roles_seeded(roles):
    assert "admin" in roles
    assert "developer" in roles

def test_user_with_role_created(developer_user):
    assert developer_user.user_roles.filter(role__name="developer").exists()
    