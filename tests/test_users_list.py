# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import json
from urllib import response

# Own
from dds_web import db
from dds_web.api import user
from dds_web.database import models
import tests

# CONFIG ################################################################################## CONFIG #

users = {
    "Researcher": "researchuser",
    "Unit Personnel": "unituser",
    "Unit Admin": "unitadmin",
    "Super Admin": "superadmin",
}

# TESTS #################################################################################### TESTS #


def get_token(username, client):
    return tests.UserAuth(tests.USER_CREDENTIALS[username]).token(client)


def test_list_unitusers_with_researcher(client):
    """Researchers cannot list unit users."""
    token = get_token(username=users["Researcher"], client=client)
    response = client.get(tests.DDSEndpoint.LIST_UNIT_USERS, headers=token)
    assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_list_unitusers_with_super_admin(client):
    """Super admins will be able to list unit users, but not right now."""
    token = get_token(username=users["Super Admin"], client=client)
    response = client.get(tests.DDSEndpoint.LIST_UNIT_USERS, headers=token)
    assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_list_unitusers_with_unit_personnel_and_admin_deactivated(client):
    """Unit Personnel should be able to list the users within a unit."""
    # Deactivate user
    for u in ["Unit Personnel", "Unit Admin"]:
        # Get token
        token = get_token(username=users[u], client=client)

        user = models.User.query.get(users[u])
        user.active = False
        db.session.commit()

        # Try to list users - should only work if active - not now
        response = client.get(tests.DDSEndpoint.LIST_UNIT_USERS, headers=token)

        # Unauth and not forbidden because the user object is not returned from the token
        assert response.status_code == http.HTTPStatus.UNAUTHORIZED


def test_list_unitusers_with_unit_personnel_and_admin_ok(client):
    # Active unit users should be able to list unit users
    for u in ["Unit Personnel", "Unit Admin"]:
        # Get token
        token = get_token(username=users[u], client=client)

        # Get users
        response = client.get(tests.DDSEndpoint.LIST_UNIT_USERS, headers=token)
        assert response.status_code == http.HTTPStatus.OK

        keys_in_response = response.json["keys"]
        unit_in_response = response.json["unit"]
        users_in_response = response.json["users"]

        assert keys_in_response

        user_object = models.User.query.get(users[u])
        assert user_object.unit.name == unit_in_response

        all_users = user_object.unit.users

        # ["Name", "Username", "Email", "Role", "Active"]
        for dbrow in user_object.unit.users:
            expected = {
                "Name": dbrow.name,
                "Username": dbrow.username,
                "Email": dbrow.primary_email,
                "Role": dbrow.role,
                "Active": dbrow.is_active,
            }
            assert expected in users_in_response
