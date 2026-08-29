import type { ReactNode } from "react";

type NavIconProps = {
  size?: number;
};

function NavGlyph({
  size = 16,
  children,
}: NavIconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="nav-icon"
      aria-hidden
    >
      {children}
    </svg>
  );
}

export function AgentsIcon({ size = 16 }: NavIconProps) {
  return (
    <NavGlyph size={size}>
      <rect
        x="4.25"
        y="4.25"
        width="15.5"
        height="15.5"
        rx="3"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      <path
        d="M8 9h8M8 12.25h8M8 15.5h5.25"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </NavGlyph>
  );
}

export function ConnectorsIcon({ size = 16 }: NavIconProps) {
  return (
    <NavGlyph size={size}>
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
    </NavGlyph>
  );
}
