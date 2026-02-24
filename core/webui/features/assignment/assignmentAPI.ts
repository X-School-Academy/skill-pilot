import { Assignment } from "../../types/assignment"

export async function fetchCount(amount = 1): Promise<{ data: number }> {
  const response = await fetch('/api/counter', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ amount }),
  })
  const result = await response.json()

  return result
}

export async function fetchAssignments( user : string ): Promise<{data: Assignment}> {
  const response = await fetch('/api/assignments', {
    method: 'POST', 
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({user})
  })
  const result = await response.json()
  return result
}