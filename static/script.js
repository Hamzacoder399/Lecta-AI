const pdf_form = document.querySelector('form')
const pdf_input = document.getElementById('PDF_input')
const submit_butn = document.getElementById('submit-btn')
let gen_notes = ""
let prompt_count = 0
const qa_input = document.getElementById('qa-input')
const qa_btn = document.getElementById('qa-btn')
const qa_ans = document.getElementById('qa_ans')
const education = document.getElementById("education");
const quiz_type = document.getElementById("question-type")
const quiz_btn = document.getElementById('quiz_btn')
const number_of_questions = document.getElementById('num_of_ques_input')
const quiz_data_output = document.getElementById('quiz-output')
const quiz_sub_btn = document.getElementById('quiz_submit_btn')
let quiz_data = []
const grading_display = document.getElementById('grading-display')

    marked.setOptions({ mangle: false, headerIds: false })

    function toggle(show, id ='loader'){
        document.getElementById(id).style.display = show ? 'block' : 'none'
}
    function show_error(message){
    const err = document.getElementById('error-msg')
    err.innerText = message
    err.style.display = 'block'
    setTimeout(() => { err.style.display = 'none' }, 7000) // auto-hides after 5s
}
    function toggleTheme(){
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light'
    document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark')
    document.getElementById('theme-toggle').textContent = isDark ? '🌙' : '☀️'
    localStorage.setItem('theme', isDark ? 'light' : 'dark')
}
    function KaTeX_and_HTML_Converter(id_element, js_var) {
        const container = document.getElementById(id_element)
            container.innerHTML = marked.parse(js_var)   
            renderMathInElement(container, {
            delimiters: [
                { left: "$$", right: "$$", display: true },
                { left: "$",  right: "$",  display: false },
                { left: "\\[", right: "\\]", display: true },
                { left: "\\(", right: "\\)", display: false }
            ],
            throwOnError: false   // silently skips if a formula is malformed
})
    }
    function convert_to_KaTeX(id_elem){
        const container = document.getElementById(id_elem)
        renderMathInElement(container, {
            delimiters: [
                { left: "$$", right: "$$", display: true },
                { left: "$",  right: "$",  display: false },
                { left: "\\[", right: "\\]", display: true },
                { left: "\\(", right: "\\)", display: false }
            ],
            throwOnError: false
})
    }

    // Remember user's preference on page load
    const savedTheme = localStorage.getItem('theme')
    if(savedTheme) document.documentElement.setAttribute('data-theme', savedTheme)

pdf_form.addEventListener('submit', function(event){
    event.preventDefault()
    submit_butn.textContent = "Processing... ⏳";
    submit_butn.disabled = true
    toggle(true)
    const file = pdf_input.files[0]
    const form_data = new FormData();
    form_data.append("pdf", file)
    fetch('/extraction', 
    {   method: 'POST', 
        body: form_data 
    })  
    .then(response => response.json())
    .then(data => {
        // Once data is back, reset the button
        submit_butn.textContent = "Extract text.";
        submit_butn.disabled = false;
        if (!data.success) {
            console.error(data.error);
            return;
        }
    

        console.log("Chunks: ", data.chunks)
        fetch('/notes',{
            method: 'POST',
            headers: {"Content-type": "application/json"},
            body: JSON.stringify({chunks: data.chunks})
        })
        .then(response => response.json())
        .then(notes_data => {
            submit_butn.textContent = "Extract text."
            submit_butn.disabled = false
            toggle(false)
            if(!notes_data.success){
                console.error(notes_data.error)
                show_error(notes_data.error)
                return
            }
            console.log("Notes:", notes_data.notes)
            gen_notes = notes_data.notes

            
            // DISPLAY NOTES, implement Markdown and apply KaTeX
            KaTeX_and_HTML_Converter("notes-container", gen_notes)
            toggle(false)
            // REVEALING ALL SECTIONS
            document.getElementById('notes-sec').style.display = 'block'
            document.getElementById('quiz_section').style.display = 'block'
            document.getElementById('qa_section').style.display = 'block' 

        })
        .catch(error => {
            console.error("Notes Error:", error);
            show_error(error.message)
            submit_butn.textContent = "Extract text.";
            submit_butn.disabled = false;
            toggle(false);
        })

        qa_btn.addEventListener('click', function(){
            const question = qa_input.value
            if (!question){
                return
            }
            toggle(true, 'qa-loader')
            fetch('/qa', {
                method: 'POST',
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    user_prompt: question,
                    prompt_count: prompt_count,
                    notes: gen_notes
                })
                })
                .then(response => response.json())
                .then(data => {
                    if (!data.success){
                        console.log(data.error)
                        show_error(data.error)
                        return
                    }
                    qa_data = data.answer
            // DISPLAY answer to question, implement Markdown and apply KaTeX
            KaTeX_and_HTML_Converter("qa_ans", qa_data)
            toggle(false, 'qa-loader')
            toggle(true, 'qa_ans')
            })
                .catch(error => {
                    console.error("QA Error:", error);
                    show_error(error.message)
                    submit_butn.textContent = "Extract text."
                    submit_butn.disabled = false;
                    toggle(false, 'qa-loader')
                    toggle(false)
                    toggle(true, 'qa_ans')
                        })
        })

        quiz_btn.addEventListener('click', function(){
            const edu_lvl = education.value
            const quiz_format = quiz_type.value
            const questions = number_of_questions.value
            console.log("Sending:", {notes: gen_notes, level_of_edu: edu_lvl, ques_type: quiz_format, number_of_questions: questions})
            if(!edu_lvl || !quiz_format || !questions){
                return
            }
            toggle(true, 'quiz-loader')
            fetch('/quiz', {
                method: 'POST',
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    notes: gen_notes,
                    level_of_edu: edu_lvl,
                    ques_type: quiz_format,
                    number_of_questions: questions
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (!data.success){
                        console.log(data.error)
                        show_error(data.error)
                        return
                    }
                    quiz_data = data.quiz
                    let quiz_html = ""
                    quiz_data.forEach(function(q, index) {
                        let ques_block = ""
                        if(quiz_format === "mcqs"){
                            // building HTML code for placing in proper quiz- only for mcqs
                            ques_block = `
                            <div class="question-block">
                                <p>${index + 1}. ${q.question}</p>
                                <label><input type="radio" name="q${index}" value="A"> A) ${q.options.A}</label>
                                <label><input type="radio" name="q${index}" value="B"> B) ${q.options.B}</label>
                                <label><input type="radio" name="q${index}" value="C"> C) ${q.options.C}</label>
                                <label><input type="radio" name="q${index}" value="D"> D) ${q.options.D}</label>
                            </div> `
                        }
                        else {
                            ques_block = `
                            <div class="question-block">
                                <p>${index + 1}. ${q.question}</p>
                                <textarea data-index="${index}" rows="3"></textarea>
                            </div>  `
                        }
                        // whatever ques_block that is HTML code comes out is then concatenated with quiz_html which is gonna be displayed on the website       
                        quiz_html += ques_block
                    })
                    quiz_data_output.innerHTML = quiz_html
                    convert_to_KaTeX("quiz-output")
                    toggle(false, 'quiz-loader')
                    toggle(true, 'quiz-output')
                    toggle(true,'quiz_submit_btn')
                })
                .catch(error => {
                    console.error("Quiz Error:", error);
                    show_error(error.message)
                    submit_butn.textContent = "Extract text.";
                    submit_butn.disabled = false;
                    toggle(false, 'quiz-loader')
                    toggle(false, 'quiz-output')
                    toggle(false,'quiz_submit_btn')
                        })
        })
        quiz_sub_btn.addEventListener('click', function(event){
            const quiz_format = quiz_type.value
            let user_ans = []
            quiz_data.forEach(function(q, index){
                let ans = ""
                if (quiz_format === "mcqs"){
                    let selected = document.querySelector('input[name="q' + index + '"]:checked')
                    ans = selected ? selected.value : "No answer is selected."
                }
                else {
                    let txt_area = document.querySelector('textarea[data-index="' + index + '"]')
                    ans = txt_area.value.trim()
            }
                user_ans.push({
                    question: q.question,
                    correct_answer: q.correct_answer || q.model_answer,
                    answers: ans
                })
            })
            toggle(true, 'quiz-sub-loader')
            fetch('/grade', {
                method: 'POST',
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    answers: user_ans,
                    notes: gen_notes,
                    question_type: quiz_format
                })
            })
            .then(response => response.json())
            .then(function(data) {
                if (!data.success){
                    console.log(data.error)
                    show_error(data.error)
                    return
                }
                else{
                    grading_data = data.grading
                    KaTeX_and_HTML_Converter("grading-display", grading_data)
                    toggle(false, 'quiz-sub-loader')
                }
            })
        })
        
    })
    .catch(error => {
        submit_butn.textContent = "Extract text."
        submit_butn.disabled = false
        toggle(false)
        toggle(false, 'qa-loader')
        toggle(false, 'quiz-loader')
        toggle(true, 'quiz-sub-loader')
        toggle(false, 'quiz-output')
        toggle(false,'quiz_submit_btn')
        toggle(true, 'qa_ans')
        console.error("Error: ", error)
    })
})
