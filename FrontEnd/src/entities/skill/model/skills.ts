export type Skill = {
  id: string;
  name: string;
  description: string;
};

export const skills: Skill[] = [
  {
    id: "onboarding",
    name: "Onboarding",
    description: "Walk new customers through setup and first value.",
  },
  {
    id: "support",
    name: "Support",
    description: "Answer product questions from trusted knowledge.",
  },
  {
    id: "lead-qualify",
    name: "Lead qualification",
    description: "Ask the right questions and score inbound leads.",
  },
];

export function getSkill(id: string | null | undefined): Skill | null {
  if (!id) return null;
  return skills.find((skill) => skill.id === id) ?? null;
}
