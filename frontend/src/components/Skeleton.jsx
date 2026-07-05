import React from 'react'
import './Skeleton.css'

export const SkeletonCard = () => (
  <div className="skeleton-card">
    <div className="skeleton-header">
      <div className="skeleton-avatar"></div>
      <div className="skeleton-text-group">
        <div className="skeleton-line short"></div>
        <div className="skeleton-line medium"></div>
      </div>
    </div>
    <div className="skeleton-content">
      <div className="skeleton-line long"></div>
      <div className="skeleton-line long"></div>
      <div className="skeleton-line medium"></div>
    </div>
  </div>
)

export const SkeletonStat = () => (
  <div className="skeleton-stat">
    <div className="skeleton-icon"></div>
    <div className="skeleton-stat-content">
      <div className="skeleton-line short"></div>
      <div className="skeleton-line medium"></div>
    </div>
  </div>
)

export const SkeletonList = ({ count = 3 }) => (
  <div className="skeleton-list">
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="skeleton-list-item">
        <div className="skeleton-line long"></div>
        <div className="skeleton-line medium"></div>
      </div>
    ))}
  </div>
)

export const SkeletonChart = () => (
  <div className="skeleton-chart">
    <div className="skeleton-chart-header">
      <div className="skeleton-line short"></div>
      <div className="skeleton-line medium"></div>
    </div>
    <div className="skeleton-chart-content">
      <div className="skeleton-bar" style={{ height: '60%' }}></div>
      <div className="skeleton-bar" style={{ height: '80%' }}></div>
      <div className="skeleton-bar" style={{ height: '45%' }}></div>
      <div className="skeleton-bar" style={{ height: '90%' }}></div>
      <div className="skeleton-bar" style={{ height: '70%' }}></div>
      <div className="skeleton-bar" style={{ height: '55%' }}></div>
      <div className="skeleton-bar" style={{ height: '75%' }}></div>
    </div>
  </div>
)

export const SkeletonMessage = () => (
  <div className="skeleton-message">
    <div className="skeleton-avatar small"></div>
    <div className="skeleton-message-content">
      <div className="skeleton-line long"></div>
      <div className="skeleton-line medium"></div>
      <div className="skeleton-line short"></div>
    </div>
  </div>
)

export default {
  Card: SkeletonCard,
  Stat: SkeletonStat,
  List: SkeletonList,
  Chart: SkeletonChart,
  Message: SkeletonMessage
}
