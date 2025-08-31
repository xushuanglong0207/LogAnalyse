'use client'

import React, { useState, ReactNode } from 'react'

// 简化版Providers组件，避免依赖问题
export function Providers({ children }: { children: ReactNode }) {
  return (
    <div>
      {children}
    </div>
  )
} 