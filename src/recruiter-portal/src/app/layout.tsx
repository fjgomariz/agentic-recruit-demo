import type { Metadata } from "next";
import { PortalShell } from "@/components/portal-shell";
import "./globals.css";

export const metadata: Metadata = { title: "Northstar Recruiter Portal", description: "Recruiter administration demo for Azure AI Foundry." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><PortalShell>{children}</PortalShell></body></html>; }
