/**
 * Agentic UI Components
 *
 * AXIS(Agentic eXperience Interface System) 기반 에이전트 협업 컴포넌트
 * A2UI/AG-UI 프로토콜 지원
 */

// Core components
export { AgentRunContainer } from './AgentRunContainer'
export type { AgentRunContainerProps } from './AgentRunContainer'

export { StepIndicator } from './StepIndicator'
export type { StepIndicatorProps, Step } from './StepIndicator'

export { StreamingText, StreamingTextList } from './StreamingText'
export type { StreamingTextProps, StreamingTextListProps } from './StreamingText'

export { SurfaceRenderer } from './SurfaceRenderer'
export type { SurfaceRendererProps } from './SurfaceRenderer'

// WF-01 Seminar Pipeline components
export { ActivityPreviewCard } from './ActivityPreviewCard'
export type { ActivityPreviewCardProps, ActivityData } from './ActivityPreviewCard'

export { AARTemplateCard } from './AARTemplateCard'
export type { AARTemplateCardProps } from './AARTemplateCard'

// Human-in-the-Loop components
export { ApprovalDialog } from './ApprovalDialog'
export type { ApprovalDialogProps, ChangeItem } from './ApprovalDialog'

export { ToolCallCard, ToolCallList } from './ToolCallCard'
export type { ToolCallCardProps, ToolCallListProps, ToolCallStatus } from './ToolCallCard'

// Collector Health & Seminar Management components
export { CollectorHealthBar } from './CollectorHealthBar'
export type {
  CollectorHealthBarProps,
  HealthStatus,
  CollectorHealthResult,
  HealthCheckData,
} from './CollectorHealthBar'

export { SeminarChatPanel } from './SeminarChatPanel'
export type { SeminarChatPanelProps, SeminarExtractResult } from './SeminarChatPanel'

export { FileUploadZone } from './FileUploadZone'
export type { FileUploadZoneProps } from './FileUploadZone'
