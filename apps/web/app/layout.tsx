import './globals.css'

export const metadata = {
  title: '$KILLSWITCH - AI Agent Safety',
  description: 'Because every AI needs an off switch.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}