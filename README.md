# Newark Drone Coders, examples 1

## Getting started

* First you need to download and install
  * Git: https://git-scm.com/downloads
  * PyCharm Community Edition: https://www.jetbrains.com/pycharm/download/

Most professional python developers use PyCharm or VSCode, we'll be using PyCharm).



* Then, clone (download) this code onto your computer by doing this
![guide/git-clone.png](guide/git-clone.png)

and please use the GitHub URL of this project: `git@github.com:epanov1602/nwk-drone-examples.git`



* When the code download ("git clone") is completed, you will see code files (modules) organized this way in your PyCharm:
![guide/project.png](guide/project.png)

^^ click on `requirements.txt`


* Once the requirements file opens, right-click on any of the lines in it (for example, `djitellopy2`) and you'll be offered to install all the packages that are needed for this code to work -- you can agree and install
![guide/requirements.png](guide/requirements.png)


* After that installation is done, you should be in good shape to run this drone code!


## Running the examples

* `car_main.py`, `copter_main.py` and `laptop_main.py` are modules (code files) that you can run in order to
  * drive a car with camera
  * fly a copter with camera
  * just play with your laptop camera

* we will be changing them in order to accomplish different things

* other modules contain various functions that are handy to have (for example, recognizing an AprilTag, or driving)

