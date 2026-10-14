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


async def accept_onboarding_token(token, user, organizations, memberships, users):
    try:
        claims = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM], options={"require": ["exp"]})
        org_id = claims["organization_id"]
        if (claims.get("type") != "organization_onboarding"
            or claims.get("email") != user.email.strip().casefold()
            or not ObjectId.is_valid(org_id)):
            raise ValueError()
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(400, "Invalid or expired organization invitation") from exc
    if not await organizations.find_one({"_id": ObjectId(org_id)}):
        raise HTTPException(404, "Organization not found")
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
