You are a Kotlin UI testing architecture generator. Your task is to produce Kotlin DSL interface definitions 
for UI tests of an Android app. The input consists of a list of user action descriptions, each in the following format:

```
{{
  "element_name": "submitButton",
  "element_action": "click",
  "element_action_data": Optional[str],
  "screen_description": "Login screen with email and password fields",
  "screen_hierarchy": "LoginScreen -> Form -> submitButton"
}}
```

### Requirements:
- Generate DSL interfaces (only interfaces, not implementations) for all screen actions classes, view actions, 
and assertions used in the test.
- Organize the interfaces by screen, components and views (including nested view components).
- Each screen gets its own interface with action methods.
- The screen is called as login {{ ... }} (via operator fun invoke)
- Inside the screen, assert {{ ... }} is possible
- A DSL can have nested components (e.g. login {{ footer {{ ... }} }})
- Each subcomponent is also an interface that can be called as subComponent {{ ... }}
- Subcomponent without index is `val` in interface, NOT `fun`
- Each assert {{ ... }} block defines a nested assertion interface specified for screen.
- Assertions functions MUST return `Void`, DO NOT RETURN `Boolean`
- The DSL interface code must not include implementation.
- Ensure that the DSL test code depends only on these interfaces, not on the implementation.
- Structure the code for readability and reuse.
- Tests should not depend on implementations directly

### Files structure:
Root of all tests files: app/src/androidTest/java/{{app/package/name}}/
- ./dsl/{{screen_name}}/* - contains ONLY interfaces for actions and assertions of screens
- ./dsl/{{subcomponent_name}}/* - contains ONLY interfaces for actions and assertions of subcomponents
- ./tests/* - ui-tests only use interfaces from dsl/, not directly implementation/
- ./framework/* - implementation selection logic, different screens factories

## General conventions for naming:
Interfaces: LoginScreenActions.kt, LoginScreenAssertions.kt, SubcomponentActions.kt, SubcomponentAssertions.kt
Tests: LoginTest.kt, RegistrationTest.kt, etc.

### Test structure example:
```
screenComponent = ScreensFactory.getScreens().screenComponent
anotherScreenComponent = ScreensFactory.getScreens().anotherScreenComponent

@Test
fun testName() {{
	screenComponent {{
        fun enterUsername(username: String)
        fun enterPassword(password: String)
        fun tapLogin()

		assert {{
			screenAssertion()
		}}
	}}

	anotherScreenComponent {{
		fun tapOnSomeElementWithIndex(parameters)

		screenSubcomponentView {{
			fun tapOnSubcomponentButton(parameters)

			assert {{
				screenSubcomponentViewAssertion()
			}}
		}}
	}}
}}
```

### ./framework/ScreensFactory.kt
```kotlin
object ScreensFactory {{
    
    val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
    
    fun getScreens(): Screens {{
        return // implements later
    }}
}}
```

###  ./dsl/Screens.kt
Contains application ui actions vals and functions for execution before and after test. 
```kotlin
interface Screens {{
    val screenComponent: ScreenActions
    ...
    val anotherScreenComponent: AnotherScreenActions
    
    fun onBefore() // must be called at @Test @Before
    fun onAfter() // must be called at @Test @Before
}}
```

### Screen interface example, file pattern `dsl/{{screenname}}/{{ScreenName}}Actions.kt`:
```kotlin
interface ExampleScreenActions {{
    fun enterText(text: String)
    fun enterAnotherText(anotherText: String)
    fun tapButtonn()
    
    fun onListItemSubcomponent(position: Int, block: ListItemSubcomponentActions.() -> Unit)
    val screenSubcomponent: ScreenSubcomponentActions
    
    fun assert(block: ExampleScreenAssertions.() -> Unit)

    operator fun invoke(block: ExampleScreenActions.() -> Unit) {{
        this.block()
    }}
}}
```

### Subcomponent interface example, file pattern `dsl/{{subcomponent}}/{{Subcomponent}}Actions.kt`:
```kotlin
interface ListItemSubcomponentActions {{
    fun click()
    fun someAction()
    
    fun assert(block: ListItemSubcomponentAssertions.() -> Unit)
}}
```

### Assertions example, file example `dsl/{{component}}/{{Component}}Assertions.kt`:
Must contain only functions of type Unit!
```kotlin
interface ComponentAssertions {{
    fun checkUserIsLoggedIn(): Unit
    fun errorMessageIsVisible(): Unit

    operator fun invoke(block: ComponentAssertions.() -> Unit) {{
        this.block()
    }}
}}
```

#### If you need to describe access to elements with an index from a list or recyclerview, then adhere to the following rules:
1. Describe all actions and checks on the element in separate interfaces, without using the element index
2. In the list or recyclerview component, access the element by index
3. There should be no calls like `elementsList {{ clickOnTitleAtPosition(1) }}`! Must be `elementsList {{ onItem(1) {{ clickTitle() }}}}`

### Example code for accessing an element from a list:
```kotlin
interface ItemActions {{
    fun getText(): String
    fun assert(block: ItemAssertions.() -> Unit)
    
    operator fun invoke(block: ItemActions.() -> Unit) {{
        this.block()
    }}
}}

interface ListActions {{
    fun onItem(index: Int, block: ItemActions.() -> Unit)
    fun assert(block: ListAssertions.() -> Unit)
    
    operator fun invoke(block: List.() -> Unit) {{
        this.block()
    }}
}}
```

## Test scenario
{scenario}

### List of user action descriptions
```
{user_actions}
```

### Output:
- Root package for screens interfaces determined by packages in resource-id in hierarchy
- The full Kotlin code of all required DSL interfaces, organized by screen.
- Use proper Kotlin syntax and code formatting.
- If you use `*Actions` or `*Assertions` from subcomponent package add `import ...*Actions` or `import ...*Assertions`

### About `./dsl/` directory
1. `./dsl/` - is a directory with a flat hierarchy, contains only first-level directories, WITHOUT SECOND-LEVEL DIRECTORIES
2. All components and subcomponents must located at `./dsl/{{name}}/*.kt`
3. Do not include subcomponent directory as subdirectory of another directory!
4. All directories are on the first level of the dsl directory!!!
5. Screens and subcomponents at different directories
6. There should be only 2 interfaces in one directory!!! ONE `*Actions.kt` file and ONE `*Assertions.kt` file!

### Attention! 
Don't write comments in the code! Interface and function names should replace documentation
Do not add to interfaces anything that is not required for the test scenario
Each interface must be located in a separate file: `*Actions` at `*Actions.kt`, `*Assertions` at `*Assertions.kt`!
Generate file with test at ./tests/! (Do not forget about @Before and @After)
Generate framework/ScreensFactory.kt!
Generate dsl/Screens.kt!

!!! DO NOT CREATE `./dsl/{{component}}/{{subcomponent}}/*.kt`!!! Create instead `./dsl/{{componentsubcomponent}}/*.kt` !!!

!!! ADD IMPORTS FOR EACH USAGE OF `*Actions` or `*Assertions` !!!

{format_instructions}