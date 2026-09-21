import React from 'react';
import {
  Text,
  StyleSheet,
  Pressable,
  ViewStyle,
  TextStyle,
} from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';
import { MobileTheme } from '../lib/theme';
import { MOBILE_SPRING_SNAPPY } from '../lib/animations';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export type ButtonVariant = 'default' | 'mint' | 'lavender' | 'outline';
export type ButtonSize = 'default' | 'sm' | 'pill';

interface ButtonProps {
  title: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  style?: ViewStyle;
  textStyle?: TextStyle;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export function Button({
  title,
  onPress,
  variant = 'default',
  size = 'default',
  style,
  textStyle,
  icon,
  disabled = false,
}: ButtonProps) {
  const scale = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const getContainerStyle = (): ViewStyle => {
    switch (variant) {
      case 'mint':
        return {
          backgroundColor: 'rgba(45, 212, 191, 0.15)',
          borderColor: 'rgba(45, 212, 191, 0.3)',
          borderWidth: 1,
        };
      case 'lavender':
        return {
          backgroundColor: MobileTheme.colors.lavender,
          borderWidth: 0,
        };
      case 'outline':
        return {
          backgroundColor: 'rgba(255, 255, 255, 0.05)',
          borderColor: MobileTheme.colors.border,
          borderWidth: 1,
        };
      default:
        return {
          backgroundColor: MobileTheme.colors.mint,
          borderWidth: 0,
        };
    }
  };

  const getTextStyle = (): TextStyle => {
    switch (variant) {
      case 'mint':
        return { color: MobileTheme.colors.mint };
      case 'lavender':
        return { color: '#1E1B2E', fontWeight: '700' };
      case 'outline':
        return { color: MobileTheme.colors.textPrimary };
      default:
        return { color: '#042F2E', fontWeight: '700' };
    }
  };

  const getSizeStyle = (): ViewStyle => {
    switch (size) {
      case 'sm':
        return { paddingVertical: 8, paddingHorizontal: 14, borderRadius: 12 };
      case 'pill':
        return { paddingVertical: 8, paddingHorizontal: 18, borderRadius: 9999 };
      default:
        return { paddingVertical: 14, paddingHorizontal: 20, borderRadius: 16 };
    }
  };

  return (
    <AnimatedPressable
      onPress={onPress}
      disabled={disabled}
      onPressIn={() => {
        scale.value = withSpring(0.96, MOBILE_SPRING_SNAPPY);
      }}
      onPressOut={() => {
        scale.value = withSpring(1, MOBILE_SPRING_SNAPPY);
      }}
      style={[
        styles.base,
        getContainerStyle(),
        getSizeStyle(),
        disabled && styles.disabled,
        animatedStyle,
        style,
      ]}
    >
      {icon}
      <Text style={[styles.text, getTextStyle(), textStyle]}>{title}</Text>
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  text: {
    fontSize: 14,
    fontWeight: '600',
  },
  disabled: {
    opacity: 0.5,
  },
});
