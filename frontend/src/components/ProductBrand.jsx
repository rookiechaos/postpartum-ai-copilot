import React from 'react'
import { Baby } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export default function ProductBrand({ as: Tag = 'div' }) {
  const { t } = useTranslation()
  return <Tag className="product-brand"><span className="product-brand-mark" aria-hidden="true">
    <Baby size={25} strokeWidth={1.6} />
  </span><span className="product-brand-name">{t('app.title')}</span></Tag>
}
