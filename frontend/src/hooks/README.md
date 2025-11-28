# Custom React Hooks

Reusable custom hooks for common functionality across the application.

## Available Hooks

### `useToast`

Manages toast notifications with automatic timeout.

**Usage:**
```jsx
import { useToast, Toast } from '../hooks';

function MyComponent() {
  const { toast, success, error, info, warning } = useToast();

  const handleClick = () => {
    success("Operation completed!");
    // error("Something went wrong!", 5000);
    // info("Just so you know...");
    // warning("Be careful!");
  };

  return (
    <div>
      <button onClick={handleClick}>Do Something</button>
      <Toast {...toast} />
    </div>
  );
}
```

**API:**
- `toast` - Current toast state object
- `success(message, duration)` - Show success toast
- `error(message, duration)` - Show error toast (default 5s)
- `info(message, duration)` - Show info toast
- `warning(message, duration)` - Show warning toast
- `showToast(message, type, duration)` - Generic show function
- `hideToast()` - Manually hide current toast

**Parameters:**
- `message` (string) - Message to display
- `duration` (number, optional) - Duration in ms before auto-hide (default: 3000)
- `type` (string) - Toast type: 'info', 'success', 'warning', 'error'

### `useAuth`

Manages admin authentication state and operations.

**Usage:**
```jsx
import { useAuth } from '../hooks';

function LoginPage() {
  const { isAuthenticated, isValidating, error, login, logout } = useAuth();

  const handleLogin = async (token) => {
    const success = await login(token);
    if (success) {
      // Navigate to admin dashboard
    }
  };

  if (isValidating) return <div>Checking authentication...</div>;

  if (isAuthenticated) {
    return <button onClick={logout}>Logout</button>;
  }

  return <LoginForm onSubmit={handleLogin} error={error} />;
}
```

**API:**
- `isAuthenticated` (boolean) - Current authentication status
- `isValidating` (boolean) - Whether validation is in progress
- `error` (string|null) - Current error message (if any)
- `login(token)` (async) - Login with admin token, returns success boolean
- `logout()` (async) - Logout, returns success boolean
- `validate()` (async) - Re-validate current authentication status

## Adding New Hooks

When creating new custom hooks:

1. Create a new file in `hooks/` directory: `useSomething.js`
2. Follow the naming convention: `use` prefix + descriptive name
3. Add comprehensive JSDoc comments
4. Export from `hooks/index.js` for convenient imports
5. Document in this README with usage examples

### Hook Template

```jsx
// frontend/src/hooks/useSomething.js
/**
 * Custom hook description
 * @param {type} param - Parameter description
 * @returns {Object} Return value description
 */
export function useSomething(param) {
  const [state, setState] = useState(initialValue);

  const doSomething = useCallback(() => {
    // Implementation
  }, [dependencies]);

  return {
    state,
    doSomething
  };
}
```

## Best Practices

- **Keep hooks focused** - Each hook should have a single responsibility
- **Use memoization** - Use `useCallback` and `useMemo` to prevent unnecessary re-renders
- **Clean up effects** - Always clean up timers, subscriptions, and event listeners
- **Document thoroughly** - Include JSDoc comments and usage examples
- **Export from index** - Always add to `hooks/index.js` for convenient imports
- **Test your hooks** - Consider using `@testing-library/react-hooks` for testing

## Related Documentation

- [React Hooks Documentation](https://react.dev/reference/react)
- [Custom Hooks Guide](https://react.dev/learn/reusing-logic-with-custom-hooks)
- [Project README](../../../README.md)
