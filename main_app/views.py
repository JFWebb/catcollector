from django.shortcuts import render, redirect
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView
from django.views.generic.detail import DetailView
# for session based auth
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Cat, Toy, Photo
from .forms import FeedingForm
# for amazon s3
import uuid
import boto3

# add these constants for amazons3 below imports
S3_BASE_URL = 'https://s3.us-east-1.amazonaws.com/'
BUCKET = 'cat-collector-jfw'
# Create your views here.

# def home(request):
#     '''
#     this is where we return a response
#     in most cases we  would render a template
#     and we'll need some data for that template
#     '''
#     return HttpResponse('<h1> Hello World </h1>')

def home(request):
  return render(request, 'home.html')

def about(request):
  return render(request, 'about.html')

@login_required
def cats_index(request):
  # ALL CATS
  # cats = Cat.objects.all()
  # just the user's cats:
  cats = Cat.objects.filter(user=request.user)
  return render(request, 'cats/index.html', { 'cats': cats })

@login_required
def cats_detail(request, cat_id):
  cat = Cat.objects.get(id=cat_id)
  # if cat: 
  # Get the toys the cat doesn't have
  toys_cat_doesnt_have = Toy.objects.exclude(id__in = cat.toys.all().values_list('id'))
  feeding_form = FeedingForm()
  return render(request, 'cats/detail.html', {
    'cat': cat, 'feeding_form': feeding_form,
    # Add the toys to be displayed
    'toys': toys_cat_doesnt_have
  })
# else:
  #   return redirect('index')


def add_feeding(request, cat_id):
  # create the ModelForm using the data in request.POST
  form = FeedingForm(request.POST)
  # validate the form
  if form.is_valid():
    # don't save the form to the db until it
    # has the cat_id assigned
    new_feeding = form.save(commit=False)
    new_feeding.cat_id = cat_id
    new_feeding.save()
  return redirect('detail', cat_id=cat_id)

@login_required
def assoc_toy(request, cat_id, toy_id):
  # Note that you can pass a toy's id instead of the whole object
  Cat.objects.get(id=cat_id).toys.add(toy_id)
  return redirect('detail', cat_id=cat_id)

#We'll be using S3_BASE_URL, BUCKETand a randomly generated key to build a unique URL used for uploading to Amazon S3 and for saving in the urlattribute or each Photoinstance.
@login_required
def add_photo(request, cat_id):
  #attempt to collect photo file data. photo-file will be the "name" attribute on the <input type="file">
  photo_file = request.FILES.get('photo-file', None)
  # use conditional logic to determine if the file is present
  if photo_file:
  # if it is present, we will create a reference to the boto3 client
    s3 = boto3.client('s3')
    # if present, create a unique id for each photo file, limited to 6 chars
    # replaces the file name before the .filetype : funny_cat.png => jdbw7f.png
    key = uuid.uuid4().hex[:6] + photo_file.name[photo_file.name.rfind('.'):]
    # then upload photo file to aws using a try/catch
    try:
    # if file upload successful, 
      s3.upload_fileobj(photo_file, BUCKET, key)
      #take the exchange url (given to us in exchange for the photo file) and save it to the database
      url = f"{S3_BASE_URL}{BUCKET}/{key}"
      # 1) create photo instance with photo model and provide cat_id as foreign key val
      photo = Photo(url=url, cat_id=cat_id)
      # ^ this only creates it in memory
      photo.save()
      # 2) now we save the photo instance to the database
    except Exception as error:
    # print an error message
      print("Error uploading photo: ", error)
  # if photo file not presentm redreict user to the origin page
  return redirect('detail', cat_id=cat_id)

#GET and POST! In one function!
  """
  A) check if the reuqest method is POST,
  we need to create a new user because form was submitted
  1) use the form data from the request to create a form/model instance of the model form
  2) validate the form to ensure it was completed
    2.2) if form not valid -- redirect the user to the signup page with an error message
  3) saving the user object to the database
  4) login the user (creates.a session for the logged in user in the database)
  5) redir3ect the user to the cats index page
  """

  """
  B) else the request is GET == the user clicked on the signup link
  1) create a blank instance of the model form
  2) provide that form instance to a registration template
  3) render the template so the user csn fill out the form
  """
def signup(request):
  error_message = ''
  # A) 
  if request.method == 'POST':
    # 1) request.POST contains all of the form inputs, this is how we access them.
    form = UserCreationForm(request.POST)
    #2) 
    if form.is_valid():
      # 3)
      user = form.save()
      # 4)
      login(request, user)
      # 5)
      return redirect('index')

    # 2.2) 
    else: 
      error_message = 'Invalid Info - Please Try Again'

  # B)
  # 1)  instantiate form without passing anything in
  form = UserCreationForm()
  # 2)
  context = {'form': form, 'error_message': error_message}
  # 3)
  return render (request, 'registration/signup.html', context)
  


class CatCreate(LoginRequiredMixin, CreateView):
  model = Cat
  fields = ['name', 'breed', 'description', 'age']
  success_url = '/cats/'

  # this is different from assigning the ID in feeding
  # because we are using a classbased view 
  #form is the cat create form
  def form_valid(self, form):
    # form.instance is an object created by the cat create object. object has a property called user. we can now access that user from within the form and assign it to the user currently logged in. 
    form.instance.user = self.request.user

    #return call to super, which calls the form valid method on the base clas
    return super().form_valid(form)

class CatUpdate(LoginRequiredMixin, UpdateView):
  model = Cat
  # Let's disallow the renaming of a cat by excluding the name field!
  fields = ['breed', 'description', 'age']

class CatDelete(LoginRequiredMixin, DeleteView):
  model = Cat
  success_url = '/cats/'

class ToyList(LoginRequiredMixin, ListView):
  model = Toy
  template_name = 'toys/index.html'

class ToyDetail(LoginRequiredMixin, DetailView):
  model = Toy
  template_name = 'toys/detail.html'

class ToyCreate(LoginRequiredMixin, CreateView):
    model = Toy
    fields = ['name', 'color']


class ToyUpdate(LoginRequiredMixin, UpdateView):
    model = Toy
    fields = ['name', 'color']


class ToyDelete(LoginRequiredMixin, DeleteView):
    model = Toy
    success_url = '/toys/'
