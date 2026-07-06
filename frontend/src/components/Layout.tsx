import { NavLink, Outlet } from 'react-router-dom'

// Icons
function HomeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  )
}

function CameraIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  )
}

function CirclesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  )
}

function UserIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  )
}

function CogIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  )
}

const sideItems = [
  { to: '/feed', label: 'Feed', Icon: HomeIcon },
  { to: '/circles', label: 'Circles', Icon: CirclesIcon },
  { to: '/profile', label: 'Profile', Icon: UserIcon },
  { to: '/settings', label: 'Settings', Icon: CogIcon },
]

export default function Layout() {
  return (
    <div className="min-h-screen bg-[#080810] text-[#f8fafc] flex flex-col">
      {/* Main content */}
      <main className="flex-1 pb-24 max-w-lg mx-auto w-full">
        <Outlet />
      </main>

      {/* Bottom nav */}
      <nav
        className="fixed bottom-0 inset-x-0 bg-[#080810]/90 backdrop-blur-xl border-t border-white/[0.06] z-40"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
        aria-label="Main navigation"
      >
        <div className="max-w-lg mx-auto flex items-end h-16 px-2 relative">
          {/* Left 2: Feed, Circles */}
          {sideItems.slice(0, 2).map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex-1 flex flex-col items-center justify-center h-full gap-0.5 text-[10px] font-medium transition-colors ${
                  isActive ? 'text-indigo-400' : 'text-slate-500 hover:text-slate-300'
                }`
              }
              aria-label={label}
            >
              {({ isActive }) => (
                <>
                  <Icon className="w-5 h-5" />
                  <span className={isActive ? 'text-indigo-400' : ''}>{label}</span>
                </>
              )}
            </NavLink>
          ))}

          {/* Center: Capture (protrudes above) */}
          <div className="flex-1 flex flex-col items-center justify-end pb-1 relative" style={{ height: '72px' }}>
            <NavLink
              to="/capture"
              aria-label="Capture"
              className="flex flex-col items-center"
            >
              {({ isActive }) => (
                <div
                  className={`w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-br from-indigo-400 to-violet-500 shadow-[0_0_20px_rgba(99,102,241,0.5)]'
                      : 'bg-gradient-to-br from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 hover:shadow-[0_0_20px_rgba(99,102,241,0.4)]'
                  }`}
                  style={{ marginBottom: '2px' }}
                >
                  <CameraIcon className="w-6 h-6 text-white" />
                </div>
              )}
            </NavLink>
          </div>

          {/* Right 2: Profile, Settings */}
          {sideItems.slice(2).map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex-1 flex flex-col items-center justify-center h-full gap-0.5 text-[10px] font-medium transition-colors ${
                  isActive ? 'text-indigo-400' : 'text-slate-500 hover:text-slate-300'
                }`
              }
              aria-label={label}
            >
              {({ isActive }) => (
                <>
                  <Icon className="w-5 h-5" />
                  <span className={isActive ? 'text-indigo-400' : ''}>{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}
