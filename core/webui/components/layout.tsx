
import type { ReactElement } from 'react'
export default function Layout({children}:any) {
  return (
    <div className='flex flex-col md:flex-row md:min-h-screen'>
      <div className='flex flex-col items-center w-full'>
        <main className='flex-1 w-full px-6 pb-20 md:pb-0'>{children}</main>
      </div>
    </div>
  )
}