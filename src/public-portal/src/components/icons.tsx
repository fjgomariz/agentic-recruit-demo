import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

const baseProps: IconProps = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

export function ArrowRightIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
}
export function BriefcaseIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18" /></svg>;
}
export function LocationIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></svg>;
}
export function ClockIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>;
}
export function SearchIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>;
}
export function SparkIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="m12 3 1.4 4.2L18 9l-4.6 1.8L12 15l-1.4-4.2L6 9l4.6-1.8L12 3ZM19 15l.7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7L19 15Z" /></svg>;
}
export function PeopleIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><circle cx="9" cy="8" r="3" /><path d="M3 20v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6M18 14a5 5 0 0 1 3 4.6V20" /></svg>;
}
export function GrowthIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M4 19V9M10 19V5M16 19v-7M22 19V3" /></svg>;
}
export function CheckIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="m5 12 4 4L19 6" /></svg>;
}
export function UploadIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M12 16V4m0 0L7 9m5-5 5 5M5 15v4h14v-4" /></svg>;
}
