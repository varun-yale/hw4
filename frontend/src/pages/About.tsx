import { Link } from 'react-router-dom'
import { Shield } from '../components/NavBar'

const values = [
  {
    icon: '✦',
    title: 'The real thing',
    text: 'Everything we carry is officially licensed, so every crest, wordmark, and bulldog is exactly right.',
  },
  {
    icon: '◐',
    title: 'Made to be worn',
    text: 'Soft fleece, easy tees, and quarter-zips you will reach for on cold walks across Old Campus.',
  },
  {
    icon: '❖',
    title: 'For the whole family',
    text: 'Styles for students and alumni, plus Mom, Dad, Grandpa, and siblings cheering from the stands.',
  },
]

export default function About() {
  return (
    <div className="about">
      <section className="about-hero">
        <div>
          <p className="eyebrow">About Campus Customs</p>
          <h1>
            A New Haven shop for <em>the Yale community.</em>
          </h1>
        </div>
        <p className="about-lede">
          Campus Customs is built around a simple idea: Yale gear should feel as good as it looks. We stock
          officially licensed apparel for every residential college, the graduate and professional schools, and
          just about every varsity sport.
        </p>
      </section>

      <section className="about-values">
        {values.map((v) => (
          <article key={v.title} className="value-card">
            <span className="value-icon" aria-hidden="true">
              {v.icon}
            </span>
            <h2>{v.title}</h2>
            <p>{v.text}</p>
          </article>
        ))}
      </section>

      <section className="about-story">
        <div className="about-quote">
          <Shield size={56} />
          <blockquote>“From your first week on campus to your twenty-fifth reunion.”</blockquote>
        </div>
        <div className="prose">
          <h2>What you'll find here</h2>
          <ul>
            <li>
              <strong>Residential college gear.</strong> Crests and quarter-zips for Morse, Branford, Saybrook, and
              the rest.
            </li>
            <li>
              <strong>Varsity styles.</strong> Hockey, sailing, squash, fencing, and more, plus shirts for The Game.
            </li>
            <li>
              <strong>Graduate and professional schools.</strong> Law, Medicine, Management, Art, Music, and others.
            </li>
            <li>
              <strong>Help when you need it.</strong> Our online assistant checks live stock in your size and
              suggests alternatives when something sells out.
            </li>
          </ul>
        </div>
      </section>

      <section className="visit-card">
        <div>
          <p className="eyebrow">Visit us</p>
          <h2>57 Broadway, New Haven, CT 06511</h2>
          <p className="muted">Stop by the shop, or browse everything online.</p>
        </div>
        <Link to="/products" className="btn btn-primary btn-lg">
          Shop the collection
        </Link>
      </section>
    </div>
  )
}
