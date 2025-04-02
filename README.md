# MiniArchive

A digital archive for *The Challenger*, our school's newspaper, offering secure access, streamlined content management, and an intuitive user experience.

## Project Origin

This project started from an informal chat during supper with Joseph, Giulio, and Richard. Recognizing the need for a web archive for *The Challenger*, I quickly developed a proposal. Within 24 hours, leveraging my knowledge of Flask and MySQL, a functional prototype was presented, impressing the team and setting the foundation for a collaborative effort.

## Technical Stack

- **Core Application**: Flask
- **Database**: MySQL
- **File Proxy Service**: Cloudflare Worker
- **Hosting**: Google Cloud Run
- **Storage**: Google Cloud Storage

### Why Flask?
Flask offers simplicity, rapid deployment, and proven reliability, making it ideal for moderate traffic scenarios.

### Database Choice
MySQL was chosen for its stability and seamless integration with Flask. Future improvements may involve migrating to MongoDB for flexibility and cost efficiency.

### File Proxy Service
A separate microservice via Cloudflare Workers was implemented to securely proxy PDF files, protecting files with expiring URLs.

## Database Structure
The database consists of four main tables:

1. **Category**: Organizes issues (`1-to-many` relationship with issues).
2. **Newspaper Issue**: Stores metadata, file paths, and access control (`view_power`).
3. **User**: Manages authentication and access levels.
4. **Config**: Stores global settings, including stopwords and "About" page content.

## Features

### User Experience
- **Homepage**: Overview and introduction.
- **Archive Viewing**: Browse issues seamlessly.
- **Date-based Navigation**: Easy access to specific issues by date.
- **Search**: Efficient keyword-based document search.
- **Document Viewing**: Secure, direct PDF viewing.

### Content Management
- **About Page Management**
- **Category Management**
- **File Uploading**
- **Issue Management**
- **Stopword Management**

### User Administration
- **Secure Authentication**
- **User Management**: Admin tools for managing user roles and permissions.
- **Admin Dashboard**: Centralized management of all settings.

### Security & Access Control
Access to sensitive articles is managed by assigning users and documents a `view_power` level. Users can only access documents matching their permission level or lower.

## Performance Optimization
Caching is implemented using `flask_caching` to optimize performance and reduce database load. Each database query function is cached, and caches are invalidated upon data modifications.

## Deployment
- **Web Service**: Deployed via Docker on Google Cloud Run, proxied with Cloudflare Workers.
- **Database**: Hosted on Google SQL with restricted access.
- **File Proxy**: Cloudflare Workers with KV storage for expiring URLs.

## Collaboration & Lessons Learned
Our small team fostered a proactive, productive atmosphere with clear communication and regular updates. However, clear and precise instructions, especially for non-technical tasks, are crucial to maintaining momentum.

## Future Enhancements
- Customizable themes (color palette, background image)
- Admin password recovery mechanism
- Migration from MySQL to MongoDB
- Potential rewrite using FastAPI and Vue.js for modernizing the tech stack
