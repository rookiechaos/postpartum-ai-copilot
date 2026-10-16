import React from 'react'
import { Baby } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export default function ProductBrand({ as: Tag = 'div' }) {
  const { t } = useTranslation()
  return <Tag className="product-brand"><Baby size={28} aria-hidden="true" /><span>{t('app.title')}</span></Tag>
}
