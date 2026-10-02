from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from server.app.notifications.repository import (
    count_unread_notifications,
    delete_notification,
    list_user_notifications,
    mark_notification_read,
)
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.organizations.policy import (
    OrganizationAction,
    require_organization_permission,
)
from server.app.quiz.repositories.v2.models.quiz_models import QuizDocumentV2
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.quiz.repositories.v2.models.reference_models import (
    FolderDocumentV2,
    QuizHistoryDocumentV2,
)
from server.app.quiz.repositories.v2.repositories.reference_repository import ReferenceV2Repository
from server.app.quiz.repositories.training_run_repository import TrainingRunRepository
from server.app.quiz.services.quiz_user_library_service import QuizUserLibraryService


@pytest.mark.asyncio
async def test_notification_reads_and_mutations_are_isolated_by_organization(test_db):
    now = datetime.now(timezone.utc)
    organization_a = str(ObjectId())
    organization_b = str(ObjectId())
    notification_a = ObjectId()
    notification_b = ObjectId()
    await test_db["notifications"].insert_many(
        [
            {
                "_id": notification_a,
                "user_id": "user-1",
                "organization_id": organization_a,
                "title": "Organization A",
                "message": "A-only notification",
                "type": "training",
                "read": False,
                "created_at": now,
                "expires_at": None,
            },
            {
                "_id": notification_b,
                "user_id": "user-1",
                "organization_id": organization_b,
                "title": "Organization B",
                "message": "B-only notification",
                "type": "training",
                "read": False,
                "created_at": now,
                "expires_at": None,
            },
        ]
    )

    notifications, has_more = await list_user_notifications(
        test_db["notifications"],
        "user-1",
        limit=20,
        skip=0,
        organization_id=organization_a,
    )

    assert [notification.id for notification in notifications] == [str(notification_a)]
    assert has_more is False
    assert await count_unread_notifications(
        test_db["notifications"], "user-1", organization_id=organization_a
    ) == 1
    assert not await mark_notification_read(
        test_db["notifications"],
        str(notification_b),
        "user-1",
        organization_id=organization_a,
    )
    assert not await delete_notification(
        test_db["notifications"],
        str(notification_b),
        "user-1",
        organization_id=organization_a,
    )
    assert (await test_db["notifications"].find_one({"_id": notification_b}))["read"] is False


@pytest.mark.asyncio
async def test_training_repository_rejects_cross_organization_quiz_run_and_assignment(test_db):
    owner_user_id = "owner-1"
    recipient_user_id = "recipient-1"
    organization_a = str(ObjectId())
    organization_b = str(ObjectId())
    quiz_a = ObjectId()
    quiz_b = ObjectId()
    run_a = ObjectId()
    run_b = ObjectId()

    await test_db["quizzes_v2"].insert_many(
        [
            {"_id": quiz_a, "owner_user_id": owner_user_id, "organization_id": organization_a, "status": "active"},
            {"_id": quiz_b, "owner_user_id": owner_user_id, "organization_id": organization_b, "status": "active"},
        ]
    )
    await test_db["training_runs"].insert_many(
        [
            {"_id": run_a, "owner_user_id": owner_user_id, "organization_id": organization_a, "status": "open", "idempotency_key": "same-key"},
            {"_id": run_b, "owner_user_id": owner_user_id, "organization_id": organization_b, "status": "open", "idempotency_key": "same-key"},
        ]
    )
    await test_db["training_assignments"].insert_one(
        {
            "_id": ObjectId(),
            "training_run_id": str(run_b),
            "recipient_user_id": recipient_user_id,
            "recipient_email": "recipient@example.com",
            "organization_id": organization_b,
        }
    )
    repository = TrainingRunRepository(
        test_db["quizzes_v2"],
        test_db["training_runs"],
        test_db["training_assignments"],
        test_db["training_audit_events"],
    )

    assert await repository.get_owned_quiz(
        str(quiz_b), owner_user_id, organization_id=organization_a
    ) is None
    assert [str(run["_id"]) for run in await repository.list_runs_for_owner(
        owner_user_id, organization_id=organization_a
    )] == [str(run_a)]
    assert await repository.get_run_for_owner(
        str(run_b), owner_user_id, organization_a
    ) is None
    assert (await repository.get_run_by_idempotency_key(
        owner_user_id, "same-key", organization_id=organization_a
    ))["_id"] == run_a
    assert await repository.list_assignments_for_recipient(
        "recipient@example.com",
        recipient_user_id,
        organization_id=organization_a,
    ) == []


@pytest.mark.asyncio
async def test_canonical_quiz_lookup_and_policy_reject_cross_organization_ids(test_db):
    organization_a = str(ObjectId())
    organization_b = str(ObjectId())
    quiz = await QuizV2Repository(test_db["quizzes_v2"]).insert_quiz(
        QuizDocumentV2(
            title="Organization B private quiz",
            quiz_type="multichoice",
            source="manual",
            owner_user_id="user-1",
            created_by_user_id="user-1",
            organization_id=organization_b,
            questions=[{"question": "Q", "correct_answer": "A"}],
        )
    )
    repository = QuizV2Repository(test_db["quizzes_v2"])
    assert await repository.find_by_id_for_organization(str(quiz.id), organization_a) is None

    context = OrganizationContext(
        organization_id=organization_a,
        organization_kind="personal",
        membership_role="owner",
        principal=OrganizationPrincipal(user_id="user-1", session_id="session-a"),
        membership={"organization_id": organization_a, "user_id": "user-1"},
    )
    with pytest.raises(Exception) as exc:
        require_organization_permission(
            context=context,
            action=OrganizationAction.CONTENT_EXPORT,
            resource=quiz.model_dump(by_alias=True),
        )
    assert getattr(exc.value, "status_code", None) == 404


@pytest.mark.asyncio
async def test_same_user_cannot_read_or_mutate_folder_or_history_from_another_organization(test_db):
    user_id = "user-1"
    organization_a = str(ObjectId())
    organization_b = str(ObjectId())
    references = ReferenceV2Repository(
        test_db["folders_v2"],
        test_db["folder_items_v2"],
        test_db["saved_quizzes_v2"],
        test_db["quiz_history_v2"],
    )
    folder = await references.insert_folder(
        FolderDocumentV2(user_id=user_id, organization_id=organization_b, name="Private B")
    )
    history = await references.insert_quiz_history(
        QuizHistoryDocumentV2(
            user_id=user_id,
            organization_id=organization_b,
            quiz_id=str(ObjectId()),
            action="generated",
        )
    )
    library = QuizUserLibraryService(
        canonical_service=object(),
        quiz_repository=object(),
        reference_repository=references,
    )

    assert await library.get_folder(
        folder_id=str(folder.id),
        user_id=user_id,
        organization_id=organization_a,
    ) is None
    assert not await library.delete_folder(
        folder_id=str(folder.id),
        user_id=user_id,
        organization_id=organization_a,
    )
    assert await library.get_quiz_history_detail(
        user_id=user_id,
        history_id=str(history.id),
        organization_id=organization_a,
    ) is None
    assert not await library.delete_quiz_history_entry(
        user_id=user_id,
        history_id=str(history.id),
        organization_id=organization_a,
    )
    assert (await test_db["folders_v2"].find_one({"_id": folder.id}))["deleted_at"] is None
    assert (await test_db["quiz_history_v2"].find_one({"_id": history.id}))["deleted_at"] is None
