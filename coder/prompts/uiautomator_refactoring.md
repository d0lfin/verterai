Refactor the following Kotlin class that uses UIAutomator2 to interact with Android UI elements:
- Move all UiObject2 elements to private class fields as val with get() via device.findObject(By...).
- Avoid code duplication — neither in selectors nor in logic.
- Remove all comments — the code should be self-documenting.
- Follow the principles of Clean Code: readability, consistency, unambiguity.
- Adhere to Kotlin idiomatic style: conciseness, use of val, apply, let, run, etc., where appropriate.
- Variable and method names should be precise, reflecting the purpose, in English.
- Make sure the class can be used as PageObject in UI tests: all actions and checks should be methods of this class, accessible publicly.

Example of element description:
```kotlin
private val loginButton: UiObject2?
        get() = device.findObject(By.textContains("Login"))
```

Transform the entire class according to these rules!

### Attention! 
Return only the source code text!
Do not use markdown!

### File Path Rules
- Each generated file must have a path that starts with: `implementation/{{screen_name}}/`
- Example correct path: `implementation/login/LoginScreenUiAutomatorActions.kt`