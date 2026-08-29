type SkillIconSize = "xs" | "sm";

const SIZE_PX: Record<SkillIconSize, number> = {
  xs: 16,
  sm: 18,
};

export function SkillIcon({ size = "xs" }: { size?: SkillIconSize }) {
  const px = SIZE_PX[size];
  return (
    <svg
      viewBox="0 0 24 24"
      width={px}
      height={px}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
      className="skill-icon"
    >
      <path
        d="M12 3.75 5 7.5v9L12 20.25l7-3.75v-9L12 3.75Z"
        stroke="currentColor"
        strokeWidth="1.35"
        strokeLinejoin="round"
      />
      <path
        d="M12 3.75v16.5M5 7.5l7 3.75 7-3.75"
        stroke="currentColor"
        strokeWidth="1.35"
        strokeLinejoin="round"
      />
      <path
        d="M5.9 9.5 11.5 10.7M5.9 12.5 11.5 13.7M5.9 15.5 11.5 16.7"
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinecap="round"
      />
    </svg>
  );
}
