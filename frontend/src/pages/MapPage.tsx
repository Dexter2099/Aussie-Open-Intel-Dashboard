import { useEffect } from 'react'
import api from '../lib/api'

export default function MapPage() {
  useEffect(() => {
    api
      .get('/events?since=48h&type=bushfire|weather|maritime')
      .then((res) => {
        console.log(res.data)
      })
      .catch((err) => {
        console.error(err)
      })
  }, [])

  return <div>Map Page</div>
}
