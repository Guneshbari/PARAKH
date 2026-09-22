import React from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { RouteGuard } from '@/components/auth/RouteGuard';

export default function UserLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RouteGuard requiredRole="applicant">
      <div className="flex flex-col md:flex-row w-full dashboard-viewport">
        <Sidebar portal="user" />
        <div className="flex-1 w-full dashboard-main-scroll overflow-y-auto">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
            {children}
          </div>
        </div>
      </div>
    </RouteGuard>
  );
}
