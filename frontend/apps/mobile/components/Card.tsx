import React from 'react';
import { View, ViewProps, StyleSheet, Pressable } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';
import { MobileTheme } from '../lib/theme';
import { MOBILE_SPRING_TACTILE } from '../lib/animations';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

interface MobileCardProps extends ViewProps {
  children: React.ReactNode;
  onPress?: () => void;
  interactive?: boolean;
}

export function Card({
  children,
  style,
  onPress,
  interactive = false,
  ...props
}: MobileCardProps) {
  const scale = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  if (onPress || interactive) {
    return (
      <AnimatedPressable
        onPress={onPress}
        onPressIn={() => {
          scale.value = withSpring(0.98, MOBILE_SPRING_TACTILE);
        }}
        onPressOut={() => {
          scale.value = withSpring(1, MOBILE_SPRING_TACTILE);
        }}
        style={[styles.card, animatedStyle, style]}
        {...props}
      >
        {children}
      </AnimatedPressable>
    );
  }

  return (
    <View style={[styles.card, style]} {...props}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: MobileTheme.colors.surface,
    borderRadius: MobileTheme.radii.card,
    padding: 20,
    borderWidth: 1,
    borderColor: MobileTheme.colors.border,
  },
});
