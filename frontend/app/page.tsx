import Search from '@/components/search/SearchPage'
import Auth from '@/components/auth/AuthPage'  
import Organization from '@/components/organization/OrgPage'
import Lead from '@/components/lead/LeadPage'

export default function RootLayout({
  children,
  params,
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
