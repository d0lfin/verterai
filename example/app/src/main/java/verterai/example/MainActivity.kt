package verterai.example

import android.app.AlertDialog
import android.os.Bundle
import android.view.KeyEvent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var editTextTask: EditText
    private lateinit var recyclerViewTasks: RecyclerView
    private lateinit var taskAdapter: TaskAdapter

    // Using StateFlow to hold the task list
    private val tasksFlow = MutableStateFlow<List<String>>(emptyList())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Initialize UI elements
        editTextTask = findViewById(R.id.editTextTask)
        recyclerViewTasks = findViewById(R.id.recyclerViewTasks)
        val buttonAdd = findViewById<View>(R.id.buttonAdd)

        // Initialize RecyclerView and adapter
        taskAdapter = TaskAdapter(
            onEditClick = { position -> editTask(position) },
            onDeleteClick = { position -> deleteTask(position) }
        )

        recyclerViewTasks.apply {
            layoutManager = LinearLayoutManager(this@MainActivity)
            adapter = taskAdapter
        }

        // Collect tasks from Flow and update UI
        lifecycleScope.launch {
            tasksFlow.collectLatest { tasks ->
                taskAdapter.submitList(tasks)
            }
        }

        // Set up click listener for Add button
        buttonAdd.setOnClickListener { addTask() }

        // Set up enter key listener for EditText
        editTextTask.setOnEditorActionListener { _, actionId, event ->
            if (actionId == EditorInfo.IME_ACTION_DONE ||
                (event != null && event.keyCode == KeyEvent.KEYCODE_ENTER && event.action == KeyEvent.ACTION_DOWN)
            ) {
                addTask()
                return@setOnEditorActionListener true
            }
            false
        }
    }

    private fun addTask() {
        val taskText = editTextTask.text.toString().trim()
        if (taskText.isNotEmpty()) {
            val currentTasks = tasksFlow.value.toMutableList()
            currentTasks.add(taskText)
            tasksFlow.value = currentTasks
            editTextTask.setText("")
        } else {
            Toast.makeText(this, "Please enter a task", Toast.LENGTH_SHORT).show()
        }
    }

    private fun editTask(position: Int) {
        val currentTasks = tasksFlow.value
        if (position >= currentTasks.size) return

        val builder = AlertDialog.Builder(this)
        val view = layoutInflater.inflate(R.layout.dialog_edit_task, null)
        val editTextEditTask = view.findViewById<EditText>(R.id.editTextEditTask)
        editTextEditTask.setText(currentTasks[position])

        builder.setView(view)
            .setTitle("Edit Task")
            .setPositiveButton("Save") { _, _ ->
                val editedTask = editTextEditTask.text.toString().trim()
                if (editedTask.isNotEmpty()) {
                    val updatedTasks = currentTasks.toMutableList()
                    updatedTasks[position] = editedTask
                    tasksFlow.value = updatedTasks
                } else {
                    Toast.makeText(this, "Task cannot be empty", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("Cancel", null)
            .create()
            .show()
    }

    private fun deleteTask(position: Int) {
        val currentTasks = tasksFlow.value
        if (position >= currentTasks.size) return

        val updatedTasks = currentTasks.toMutableList()
        updatedTasks.removeAt(position)
        tasksFlow.value = updatedTasks
    }

    // RecyclerView adapter using ListAdapter with DiffUtil
    private class TaskAdapter(
        private val onEditClick: (Int) -> Unit,
        private val onDeleteClick: (Int) -> Unit
    ) : ListAdapter<String, TaskAdapter.TaskViewHolder>(TaskDiffCallback()) {

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): TaskViewHolder {
            val view = LayoutInflater.from(parent.context)
                .inflate(R.layout.item_task, parent, false)
            return TaskViewHolder(view, onEditClick, onDeleteClick)
        }

        override fun onBindViewHolder(holder: TaskViewHolder, position: Int) {
            holder.bind(getItem(position))
        }

        class TaskViewHolder(
            itemView: View,
            private val onEditClick: (Int) -> Unit,
            private val onDeleteClick: (Int) -> Unit
        ) : RecyclerView.ViewHolder(itemView) {

            private val textViewTask: TextView = itemView.findViewById(R.id.textViewTask)
            private val buttonEdit: View = itemView.findViewById(R.id.buttonEdit)
            private val buttonDelete: View = itemView.findViewById(R.id.buttonDelete)

            init {
                buttonEdit.setOnClickListener { onEditClick(adapterPosition) }
                buttonDelete.setOnClickListener { onDeleteClick(adapterPosition) }
            }

            fun bind(task: String) {
                textViewTask.text = task
            }
        }

        class TaskDiffCallback : DiffUtil.ItemCallback<String>() {
            override fun areItemsTheSame(oldItem: String, newItem: String): Boolean {
                return oldItem === newItem
            }

            override fun areContentsTheSame(oldItem: String, newItem: String): Boolean {
                return oldItem == newItem
            }
        }
    }
}
