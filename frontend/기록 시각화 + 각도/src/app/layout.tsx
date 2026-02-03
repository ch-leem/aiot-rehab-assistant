// app/layout.tsx
import "./globals.css";

export const metadata = {
  title: "Clinical Pose Viewer",
  description: "3D pose + sensor visualization for clinicians",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
