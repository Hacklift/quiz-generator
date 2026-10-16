"""Email-bound organization enrollment. Ordinary membership never sets language provenance."""
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import jwt
from fastapi import HTTPException
from server.app.core.config import settings
from server.app.organizations.services import get_organization_settings


async def issue_onboarding_token(organization_id, email, user, organizations, memberships):
    org = await get_organization_settings(organization_id, user, organizations, memberships)
    if org.role not in {"owner", "admin"}:
        raise HTTPException(403, "Organization administrator access required")
    return jwt.encode({
        "type": "organization_onboarding", "organization_id": organization_id,
        "email": email.strip().casefold(), "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def validate_onboarding_token(token, organizations, *, email=None):
    """Read invitation context without enrolling anyone or exposing the invitee email."""
    try:
        claims = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM], options={"require": ["exp"]})
        org_id = claims["organization_id"]
        if (claims.get("type") != "organization_onboarding"
            or not isinstance(claims.get("email"), str) or not claims["email"].strip()
            or (email is not None and claims["email"] != email.strip().casefold())
            or not ObjectId.is_valid(org_id)):
            raise ValueError()
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError) as exc:
        raise HTTPException(400, "Invalid or expired organization invitation") from exc
    organization = await organizations.find_one({"_id": ObjectId(org_id)})
    if not organization:
        raise HTTPException(404, "Organization not found")
    return organization


async def enroll_onboarding_user(org_id, user, memberships, users):
    """Enroll only after the caller validates an email-bound invitation.

    Registration may enroll an unverified account, but does not mark its email
    verified or bypass verified-user authorization on organization resources.
    """
    now = datetime.now(timezone.utc)
    await memberships.update_one(
        {"organization_id": org_id, "user_id": user.id},
        {"$setOnInsert": {"role": "member", "created_at": now, "updated_at": now, "source": "onboarding"}},
        upsert=True,
    )
    # Do not change an existing explicit language, or replace previous provenance.
    await users.update_one(
        {"_id": ObjectId(user.id), "profile.onboarding_organization_id": None},
        {"$set": {"profile.onboarding_organization_id": org_id, "updated_at": now}},
    )
    return {"organization_id": org_id}


async def accept_onboarding_token(token, user, organizations, memberships, users):
    organization = await validate_onboarding_token(token, organizations, email=user.email)
    return await enroll_onboarding_user(str(organization["_id"]), user, memberships, users)
