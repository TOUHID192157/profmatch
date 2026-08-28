"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Search,
  Target,
  Heart,
  UserCircle,
  Settings,
  LogOut,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/matches", label: "Find Professors", icon: Search },
  { href: "/saved", label: "Saved", icon: Heart },
  { href: "/profile", label: "My Research Profile", icon: UserCircle },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    router.push("/login");
  };

  return (
    <aside className="fixed left-0 top-0 flex h-screen w-60 flex-col border-r border-[#1C2029] bg-[#0B0D12] px-4 py-6">
      <div
        className="mb-8 px-2 text-sm font-semibold tracking-wide text-[#F5F6F8]"
        style={{ fontFamily: "var(--font-display)" }}
      >
        PROFMATCH
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                active
                  ? "bg-[#4DA8FF]/10 text-[#4DA8FF]"
                  : "text-[#9AA3B2] hover:bg-[#1C2029] hover:text-[#F5F6F8]"
              }`}
            >
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="flex flex-col gap-1 border-t border-[#1C2029] pt-4">
        <button className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-[#9AA3B2] hover:bg-[#1C2029] hover:text-[#F5F6F8]">
          <Settings size={18} />
          Settings
        </button>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-[#9AA3B2] hover:bg-[#1C2029] hover:text-red-400"
        >
          <LogOut size={18} />
          Log Out
        </button>
      </div>
    </aside>
  );
}