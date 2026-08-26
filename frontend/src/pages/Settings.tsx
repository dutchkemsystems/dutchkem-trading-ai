import { User, Bell, Key, Shield, CreditCard } from 'lucide-react'

export default function Settings() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-display font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">Manage your account and platform preferences</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Profile */}
        <div className="card col-span-2 space-y-4">
          <div className="flex items-center gap-3">
            <User className="w-5 h-5 text-fortress-400" />
            <h2 className="font-display font-semibold text-white">Profile</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-400 block mb-1">Name</label>
              <input type="text" value="Dutchkem Ventures" className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-fortress-500" />
            </div>
            <div>
              <label className="text-sm text-gray-400 block mb-1">Email</label>
              <input type="email" value="admin@dutchkem.com" className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-fortress-500" />
            </div>
            <div>
              <label className="text-sm text-gray-400 block mb-1">Company</label>
              <input type="text" value="Dutchkem Ventures Ltd" className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-fortress-500" />
            </div>
            <div>
              <label className="text-sm text-gray-400 block mb-1">Country</label>
              <input type="text" value="Nigeria" className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-fortress-500" />
            </div>
          </div>
          <button className="btn-primary mt-2">Save Changes</button>
        </div>

        {/* Quick Settings */}
        <div className="space-y-4">
          <div className="card">
            <div className="flex items-center gap-3 mb-4">
              <Bell className="w-5 h-5 text-amber-400" />
              <h2 className="font-display font-semibold text-white text-sm">Notifications</h2>
            </div>
            <div className="space-y-3">
              {['Low balance alerts', 'Invoice ready', 'Security events', 'Usage reports'].map((item) => (
                <div key={item} className="flex items-center justify-between">
                  <span className="text-sm text-gray-300">{item}</span>
                  <div className="w-8 h-5 rounded-full bg-fortress-600 relative cursor-pointer">
                    <div className="w-4 h-4 rounded-full bg-white absolute top-0.5 translate-x-3.5" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="flex items-center gap-3 mb-4">
              <Key className="w-5 h-5 text-purple-400" />
              <h2 className="font-display font-semibold text-white text-sm">API Keys</h2>
            </div>
            <div className="space-y-2">
              <div className="p-3 rounded-xl bg-gray-800/50 flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-400">Production Key</p>
                  <p className="font-mono text-xs text-white">dk_prod_****...x8f2</p>
                </div>
                <span className="text-xs text-fortress-400">Active</span>
              </div>
              <button className="btn-secondary text-xs w-full">Generate New Key</button>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center gap-3 mb-4">
              <Shield className="w-5 h-5 text-red-400" />
              <h2 className="font-display font-semibold text-white text-sm">Security</h2>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">2FA</span>
                <span className="text-xs text-fortress-400">Enabled</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">Login alerts</span>
                <span className="text-xs text-fortress-400">On</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
