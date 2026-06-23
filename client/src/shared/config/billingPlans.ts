export type BillingPlanAction = "free" | "monthly" | "yearly";

export interface BillingPlanDefinition {
  plan: string;
  billingPeriod: string;
  price: string;
  action: BillingPlanAction;
  features: string[];
}

export interface BillingComparisonRow {
  label: string;
  free: string;
  monthly: string;
  yearly: string;
}

export const billingPlans: BillingPlanDefinition[] = [
  {
    plan: "Free",
    billingPeriod: "",
    price: "$0",
    action: "free",
    features: [
      "Generate up to 5 quizzes per month",
      "Basic question types",
      "Save and share quizzes",
      "Access to community quiz templates",
    ],
  },
  {
    plan: "Pro",
    billingPeriod: "Monthly",
    price: "$20",
    action: "monthly",
    features: [
      "Unlimited quiz generation",
      "Advanced question types",
      "Edit and customize questions",
      "Export in multiple formats",
      "Priority support",
    ],
  },
  {
    plan: "Premium",
    billingPeriod: "Yearly",
    price: "$100",
    action: "yearly",
    features: [
      "Everything in Pro",
      "Early access to new features",
      "Personalized templates",
      "Premium support",
    ],
  },
];

export const billingComparisonRows: BillingComparisonRow[] = [
  {
    label: "Quiz generation",
    free: "5 per month",
    monthly: "Unlimited",
    yearly: "Unlimited",
  },
  {
    label: "Question types",
    free: "Basic",
    monthly: "Advanced",
    yearly: "Advanced + early access",
  },
  {
    label: "Exports",
    free: "Standard share only",
    monthly: "Multiple formats",
    yearly: "Multiple formats",
  },
  {
    label: "Templates",
    free: "Community only",
    monthly: "Custom editing",
    yearly: "Personalized templates",
  },
  {
    label: "Support",
    free: "Standard",
    monthly: "Priority",
    yearly: "Premium",
  },
];
