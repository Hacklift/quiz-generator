import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import "@features/locale/i18n";
import {
  PERSONA_CATEGORIES,
  PERSONA_USER_TYPES,
  getCategoryDefinition,
  getUserTypeDefinition,
  type PersonaCategory,
  type PersonaUserType,
  type PersonaCategoryDefinition,
  type PersonaUserTypeDefinition,
} from "@shared/config/persona";

/** Translate display copy only; identity, URLs and generation enum values stay stable. */
export function usePersonaCopy() {
  const { t, i18n } = useTranslation("persona");
  return useMemo(() => {
    const roles = Object.fromEntries(
      PERSONA_USER_TYPES.map((id) => [
        id,
        {
          ...getUserTypeDefinition(id),
          label: t(`roles.${id}.label`),
          description: t(`roles.${id}.description`),
          defaultTopic: t(`roles.${id}.defaultTopic`),
        },
      ]),
    ) as Record<PersonaUserType, PersonaUserTypeDefinition>;
    const categories = Object.fromEntries(
      PERSONA_CATEGORIES.map((id) => [
        id,
        {
          ...getCategoryDefinition(id),
          label: t(`categories.${id}.label`),
          description: t(`categories.${id}.description`),
          userTypes: getCategoryDefinition(id).userTypes.map(
            (role) => roles[role.slug],
          ),
        },
      ]),
    ) as Record<PersonaCategory, PersonaCategoryDefinition>;
    return { t, roles, categories };
  }, [t, i18n.resolvedLanguage]);
}
