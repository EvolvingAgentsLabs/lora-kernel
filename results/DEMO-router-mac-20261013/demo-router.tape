# VHS tape: the recording IS the run (results/DEMO-router-mac-20261013/BRIEF.md)
Output docs/img/demo-router.gif
Set Shell "bash"
Set FontSize 18
Set Width 1400
Set Height 760
Set Padding 24
Set Theme "Builtin Solarized Light"
Set TypingSpeed 35ms
Hide
Type "cd ~/evolvingagents/lora-kernel && export PS1='$ ' && alias python=~/lora-kernel-models/venv/bin/python && clear"
Enter
Show
Type "python -m examples.tracker.demo_router --out results/DEMO-router-mac-20261013/demo.json"
Sleep 400ms
Enter
Wait+Line@240s /^\$\s*$/
Sleep 4s
