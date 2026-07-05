import React, { useState, useEffect } from 'react'
import { Users, UserPlus, X, Crown, Shield, User, Eye, FileText, CheckSquare } from 'lucide-react'
import api from '../utils/api'
import './FamilySharing.css'

function FamilySharing({ userId }) {
  const [families, setFamilies] = useState([])
  const [selectedFamily, setSelectedFamily] = useState(null)
  const [members, setMembers] = useState([])
  const [sharedData, setSharedData] = useState([])
  const [familySummary, setFamilySummary] = useState(null)
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newFamilyName, setNewFamilyName] = useState('')
  const [inviteUserId, setInviteUserId] = useState('')
  const [activeTab, setActiveTab] = useState('members') // 'members', 'summary', 'tasks'
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [newTaskDescription, setNewTaskDescription] = useState('')

  useEffect(() => {
    loadFamilies()
  }, [userId])

  useEffect(() => {
    if (selectedFamily) {
      loadFamilyMembers(selectedFamily.family_id)
      loadSharedData(selectedFamily.family_id)
      loadFamilySummary(selectedFamily.family_id)
    }
  }, [selectedFamily])
  
  const loadFamilySummary = async (familyId) => {
    try {
      const response = await api.get(`/api/families/${familyId}/summary?period=daily`)
      setFamilySummary(response)
    } catch (error) {
      console.error('Failed to load family summary:', error)
    }
  }
  
  const createTask = async (e) => {
    e.preventDefault()
    if (!newTaskTitle.trim() || !selectedFamily) return
    
    try {
      await api.post(`/api/families/${selectedFamily.family_id}/tasks`, {
        title: newTaskTitle,
        description: newTaskDescription,
        priority: 'medium'
      })
      setNewTaskTitle('')
      setNewTaskDescription('')
      // Reload tasks if needed
    } catch (error) {
      console.error('Failed to create task:', error)
    }
  }

  const loadFamilies = async () => {
    setLoading(true)
    try {
      const data = await api.get('/api/families')
      setFamilies(data || [])
      if (data && data.length > 0 && !selectedFamily) {
        setSelectedFamily(data[0])
      }
    } catch (error) {
      console.error('Failed to load families:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadFamilyMembers = async (familyId) => {
    try {
      const response = await api.get(`/api/families/${familyId}/members`)
      setMembers(response.members || [])
    } catch (error) {
      console.error('Failed to load members:', error)
    }
  }

  const loadSharedData = async (familyId) => {
    try {
      const response = await api.get(`/api/families/${familyId}/shared-data?days=7`)
      setSharedData(response.data || [])
    } catch (error) {
      console.error('Failed to load shared data:', error)
    }
  }

  const createFamily = async (e) => {
    e.preventDefault()
    if (!newFamilyName.trim()) return

    try {
      const family = await api.post('/api/families', { name: newFamilyName })
      setFamilies([...families, family])
      setSelectedFamily(family)
      setShowCreateForm(false)
      setNewFamilyName('')
    } catch (error) {
      console.error('Failed to create family:', error)
    }
  }

  const inviteMember = async (e) => {
    e.preventDefault()
    if (!inviteUserId.trim() || !selectedFamily) return

    try {
      await api.post(`/api/families/${selectedFamily.family_id}/invite`, {
        invitee_user_id: inviteUserId,
        role: 'member'
      })
      setInviteUserId('')
      loadFamilyMembers(selectedFamily.family_id)
    } catch (error) {
      console.error('Failed to invite member:', error)
    }
  }

  const getRoleIcon = (role) => {
    switch (role) {
      case 'owner':
        return <Crown size={16} />
      case 'admin':
        return <Shield size={16} />
      case 'viewer':
        return <Eye size={16} />
      default:
        return <User size={16} />
    }
  }

  return (
    <div className="family-sharing">
      <div className="family-header">
        <h2><Users size={24} /> Family Sharing</h2>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="create-family-btn"
        >
          <UserPlus size={18} /> Create Family
        </button>
      </div>

      {showCreateForm && (
        <form onSubmit={createFamily} className="create-family-form">
          <input
            type="text"
            value={newFamilyName}
            onChange={(e) => setNewFamilyName(e.target.value)}
            placeholder="Family name"
            required
          />
          <div className="form-actions">
            <button type="submit">Create</button>
            <button type="button" onClick={() => setShowCreateForm(false)}>Cancel</button>
          </div>
        </form>
      )}

      {families.length === 0 && !loading ? (
        <div className="no-families">
          <p>No families yet. Create one to start sharing!</p>
        </div>
      ) : (
        <div className="family-content">
          <div className="family-list">
            {families.map(family => (
              <div
                key={family.family_id}
                className={`family-item ${selectedFamily?.family_id === family.family_id ? 'active' : ''}`}
                onClick={() => setSelectedFamily(family)}
              >
                <h3>{family.name}</h3>
                <span className="family-id">{family.family_id}</span>
              </div>
            ))}
          </div>

          {selectedFamily && (
            <div className="family-details">
              <div className="family-tabs">
                <button
                  className={activeTab === 'members' ? 'active' : ''}
                  onClick={() => setActiveTab('members')}
                >
                  <Users size={18} /> Members
                </button>
                <button
                  className={activeTab === 'summary' ? 'active' : ''}
                  onClick={() => setActiveTab('summary')}
                >
                  <FileText size={18} /> Summary
                </button>
                <button
                  className={activeTab === 'tasks' ? 'active' : ''}
                  onClick={() => setActiveTab('tasks')}
                >
                  <CheckSquare size={18} /> Tasks
                </button>
              </div>
              
              {activeTab === 'members' && (
              <div className="members-section">
                <h3>Members</h3>
                <form onSubmit={inviteMember} className="invite-form">
                  <input
                    type="text"
                    value={inviteUserId}
                    onChange={(e) => setInviteUserId(e.target.value)}
                    placeholder="User ID to invite"
                    required
                  />
                  <button type="submit">Invite</button>
                </form>
                <div className="members-list">
                  {members.map(member => (
                    <div key={member.id} className="member-item">
                      <div className="member-info">
                        {getRoleIcon(member.role)}
                        <span>{member.user_id}</span>
                        <span className="role-badge">{member.role}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="shared-data-section">
                <h3>Shared Data (Last 7 days)</h3>
                <div className="shared-data-list">
                  {sharedData.length === 0 ? (
                    <p>No shared data yet</p>
                  ) : (
                    sharedData.map(entry => (
                      <div key={entry.id} className="data-entry">
                        <div className="entry-header">
                          <span className="entry-type">{entry.entry_type}</span>
                          <span className="entry-user">{entry.user_id}</span>
                        </div>
                        <div className="entry-time">
                          {new Date(entry.timestamp).toLocaleString()}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
              )}
              
              {activeTab === 'summary' && familySummary && (
                <div className="summary-section">
                  <h3>Daily Summary for Partner</h3>
                  <div className="summary-card">
                    <p className="summary-date">Date: {new Date(familySummary.summary?.date || familySummary.summary?.week_start).toLocaleDateString()}</p>
                    <p className="summary-text">{familySummary.summary?.summary || 'No summary available yet'}</p>
                    <p className="summary-meta">
                      {familySummary.shared_entries_count} entries tracked • {familySummary.members_count} family members
                    </p>
                  </div>
                </div>
              )}
              
              {activeTab === 'tasks' && (
                <div className="tasks-section">
                  <h3>Family Tasks</h3>
                  <form onSubmit={createTask} className="create-task-form">
                    <input
                      type="text"
                      value={newTaskTitle}
                      onChange={(e) => setNewTaskTitle(e.target.value)}
                      placeholder="Task title"
                      required
                    />
                    <textarea
                      value={newTaskDescription}
                      onChange={(e) => setNewTaskDescription(e.target.value)}
                      placeholder="Task description (optional)"
                      rows="2"
                    />
                    <button type="submit">Create Task</button>
                  </form>
                  <div className="tasks-list">
                    {tasks.length === 0 ? (
                      <p>No tasks yet. Create one to coordinate with your family!</p>
                    ) : (
                      tasks.map(task => (
                        <div key={task.task_id} className="task-item">
                          <h4>{task.title}</h4>
                          {task.description && <p>{task.description}</p>}
                          <span className="task-status">{task.status}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default FamilySharing
