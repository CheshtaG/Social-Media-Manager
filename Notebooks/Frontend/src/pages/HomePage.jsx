import { useNavigate } from 'react-router-dom'
import './HomePage.css'

const OPTIONS = [
  { id: 'reel', label: 'Make a reel' },
  { id: 'post', label: 'Make a post' },
  { id: 'story', label: 'Make a story' },
]

function HomePage() {
  const navigate = useNavigate()

  const handleOption = (id) => {
    if (id === 'reel') {
      navigate('/create/reel')
    } else {
      navigate('/generate', { state: { type: id } })
    }
  }

  return (
    <div className="home-page">
      <h1 className="home-title">What would you like to create?</h1>
      <div className="home-boxes">
        {OPTIONS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            className="home-box"
            onClick={() => handleOption(id)}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default HomePage
