import { Composition } from 'remotion'
import {
  SlideMotion,
  calculateSlideMetadata,
  defaultSlideProps,
} from './SlideMotion'

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="SlideMotion"
      component={SlideMotion}
      durationInFrames={150}
      fps={30}
      width={1080}
      height={1350}
      defaultProps={defaultSlideProps}
      calculateMetadata={calculateSlideMetadata}
    />
  )
}
