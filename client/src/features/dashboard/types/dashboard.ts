import type { User } from "@features/auth/types/User";
import type { Persona } from "@shared/config/persona";

/**
 * [SCAFFOLD-OWNED] The contract every persona view receives.
 *
 * Adding a field here changes nine files at once — raise it in the PR that
 * needs it rather than editing this in a view ticket.
 */
export interface DashboardViewProps {
  persona: Persona;
  user: User;
}
